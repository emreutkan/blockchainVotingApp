import hashlib
import time
import json
from flask import Flask, request, jsonify
import requests

# Define a Block class
class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data  # Stores the vote or transaction
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{self.data}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        while self.hash[:difficulty] != "0" * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()


# Define a Blockchain class
class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 2
        self.voters = set()  # Track voters to prevent duplicate votes

    def create_genesis_block(self):
        return Block(0, "0", time.time(), "Genesis Block")

    def get_latest_block(self):
        return self.chain[-1]

    def add_vote(self, voter_id, candidate):
        if voter_id in self.voters:
            return False, "Duplicate vote detected!"

        vote_data = f"Voter: {voter_id}, Candidate: {candidate}"
        new_block = Block(len(self.chain), self.get_latest_block().hash, time.time(), vote_data)
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.voters.add(voter_id)
        return True, "Vote successfully recorded!"

    def is_chain_valid(self, chain):
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i - 1]

            if current_block["hash"] != hashlib.sha256(
                f"{current_block['index']}{current_block['previous_hash']}{current_block['timestamp']}{current_block['data']}{current_block['nonce']}".encode()
            ).hexdigest():
                return False

            if current_block["previous_hash"] != previous_block["hash"]:
                return False

        return True

    def replace_chain(self, new_chain):
        if len(new_chain) > len(self.chain) and self.is_chain_valid(new_chain):
            self.chain = [Block(**block) for block in new_chain]
            return True
        return False

# Initialize Flask app
app = Flask(__name__)
blockchain = Blockchain()

# List of peer nodes (simulating decentralized nodes)
peers = []

# Route to add a new vote
@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    voter_id = data.get("voter_id")
    candidate = data.get("candidate")

    success, message = blockchain.add_vote(voter_id, candidate)
    if success:
        announce_new_block(blockchain.chain[-1])
        return jsonify({"message": message}), 201
    return jsonify({"error": message}), 400

# Route to get the blockchain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = [block.__dict__ for block in blockchain.chain]
    return jsonify({"length": len(chain_data), "chain": chain_data}), 200

# Route to register a new peer
@app.route('/register_node', methods=['POST'])
def register_node():
    node = request.get_json().get("node_address")
    if node not in peers:
        peers.append(node)
        return jsonify({"message": f"Node {node} added to network"}), 200
    return jsonify({"error": "Node already exists"}), 400

# Route to synchronize the blockchain
@app.route('/sync', methods=['GET'])
def sync():
    global blockchain
    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get(f"{node}/chain")
        if response.status_code == 200:
            length = response.json()["length"]
            chain = response.json()["chain"]

            if length > current_len and blockchain.is_chain_valid(chain):
                current_len = length
                longest_chain = chain

    if longest_chain:
        blockchain.replace_chain(longest_chain)
        return jsonify({"message": "Blockchain updated"}), 200
    return jsonify({"message": "Blockchain already up to date"}), 200

# Announce new block to all peers
def announce_new_block(block):
    for node in peers:
        requests.post(f"{node}/vote", json=block.__dict__)

# Run the app
if __name__ == '__main__':
    app.run(port=8000)
