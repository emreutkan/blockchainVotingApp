import datetime
import hashlib
import json
import os
from flask import Flask, jsonify, request, render_template
import requests
from urllib.parse import urlparse

# Blockchain class definition
class Blockchain:
    def __init__(self):
        """
        Initialize the Blockchain.
        - Loads the existing chain from 'chain.json' if available.
        - Validates the loaded chain. If invalid, sets the chain as invalid without resetting.
        - If no chain exists, creates the genesis block.
        """
        self.chain = []  # The blockchain
        self.current_votes = []  # List of pending votes
        self.peers = set()  # Set of peer addresses
        self.is_valid = True  # Flag to indicate chain validity

        if os.path.exists('chain.json'):
            self.load_chain()
            if not self.is_chain_valid():
                print("Invalid chain detected. Manual intervention required.")
                self.is_valid = False
                # Do not reset the chain automatically
        else:
            self.create_block(proof=1, previous_hash='0')  # Create the genesis block

    def create_block(self, proof, previous_hash):
        """
        Create a new block in the blockchain.

        Parameters:
        - proof (int): The proof given by the Proof of Work algorithm.
        - previous_hash (str): Hash of the previous block.

        Returns:
        - dict: The newly created block with its hash.
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'votes': self.current_votes,
            'proof': proof,
            'previous_hash': previous_hash
        }
        self.current_votes = []
        block_hash = self.hash(block)  # Compute the hash without the 'hash' field
        block_with_hash = block.copy()
        block_with_hash['hash'] = block_hash  # Add the 'hash' field
        self.chain.append(block_with_hash)
        self.save_chain()
        return block_with_hash

    def get_previous_block(self):
        """
        Retrieve the last block in the chain.

        Returns:
        - dict: The last block in the blockchain.
        """
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        """
        Simple Proof of Work Algorithm:
        - Find a number 'new_proof' such that hash(new_proof^2 - previous_proof^2) contains leading 4 zeroes.

        Parameters:
        - previous_proof (int): The proof of the previous block.

        Returns:
        - int: The new proof.
        """
        new_proof = previous_proof + 1  # Ensure new_proof > previous_proof
        check_proof = False
        while not check_proof:
            # Calculate hash using the positive difference
            hash_operation = hashlib.sha256(
                str(new_proof ** 2 - previous_proof ** 2).encode()
            ).hexdigest()
            # Difficulty condition: hash must start with "0000"
            if hash_operation[:4] == "0000":
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        """
        Creates a SHA-256 hash of a block.
        The 'hash' field is excluded to prevent circular dependencies.

        Parameters:
        - block (dict): The block to hash.

        Returns:
        - str: The SHA-256 hash of the block.
        """
        block_copy = block.copy()
        block_copy.pop('hash', None)  # Remove 'hash' if present
        encoded_block = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain=None):
        """
        Determines if a given blockchain is valid.

        Parameters:
        - chain (list, optional): The blockchain to validate. Defaults to self.chain.

        Returns:
        - bool: True if valid, False otherwise.
        """
        if chain is None:
            chain = self.chain

        if not chain:
            return False

        previous_block = chain[0]
        block_index = 1

        while block_index < len(chain):
            block = chain[block_index]
            # Exclude the 'hash' field when validating
            block_data = block.copy()
            block_hash = block_data.pop('hash', None)
            # Recompute the hash and compare
            if block_hash != self.hash(block_data):
                print(f"Invalid hash at block {block['index']}")
                return False
            # Check if the previous hash matches
            if block['previous_hash'] != self.hash(previous_block):
                print(f"Invalid previous hash at block {block['index']}")
                return False
            # Verify the proof of work
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(
                str(proof ** 2 - previous_proof ** 2).encode()
            ).hexdigest()
            if hash_operation[:4] != "0000":
                print(f"Invalid proof of work at block {block['index']}")
                return False
            previous_block = block
            block_index += 1
        return True

    def is_valid_proof(self, previous_proof, proof):
        """
        Validates the Proof: Does hash(proof^2 - previous_proof^2) contain 4 leading zeroes?

        Parameters:
        - previous_proof (int): The proof of the previous block.
        - proof (int): The proof to validate.

        Returns:
        - bool: True if valid, False otherwise.
        """
        hash_operation = hashlib.sha256(
            str(proof ** 2 - previous_proof ** 2).encode()
        ).hexdigest()
        return hash_operation[:4] == "0000"

    def add_vote(self, voter_id, candidate):
        """
        Adds a new vote to the list of current votes after ensuring no duplicate votes.

        Parameters:
        - voter_id (str): The unique identifier of the voter.
        - candidate (str): The name of the candidate being voted for.

        Returns:
        - int: The index of the block where the vote will be added.

        Raises:
        - ValueError: If the voter has already cast a vote.
        """
        # Check if the voter has already voted
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_id'] == voter_id:
                    raise ValueError("Voter has already cast a vote.")
        self.current_votes.append({'voter_id': voter_id, 'candidate': candidate})
        return len(self.chain) + 1

    def save_chain(self):
        """
        Saves the current blockchain to 'chain.json'.
        """
        with open('chain.json', 'w') as file:
            json.dump(self.chain, file, indent=4)

    def load_chain(self):
        """
        Loads the blockchain from 'chain.json'.
        """
        with open('chain.json', 'r') as file:
            self.chain = json.load(file)
        self.current_votes = []

    def register_peer(self, address):
        """
        Registers a new peer address.

        Parameters:
        - address (str): The address of the peer to register.
        """
        self.peers.add(address)

    def broadcast_block(self, block):
        """
        Broadcasts a newly mined block to all registered peers.

        Parameters:
        - block (dict): The newly mined block to broadcast.
        """
        for peer in self.peers:
            try:
                response = requests.post(f"{peer}/receive_block", json={"block": block})
                if response.status_code == 200:
                    print(f"Block successfully sent to {peer}")
            except requests.exceptions.RequestException as e:
                print(f"Error sending block to {peer}: {e}")

    def resolve_conflicts(self):
        """
        Resolves conflicts by replacing the chain with the longest valid chain among peers.

        Returns:
        - bool: True if the chain was replaced, False otherwise.
        """
        neighbours = self.peers
        new_chain = None
        max_length = len(self.chain)

        for peer in neighbours:
            try:
                response = requests.get(f"{peer}/chain")
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException as e:
                print(f"Error fetching chain from {peer}: {e}")

        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True

        return False

# Instantiate Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
blockchain = Blockchain()

# Endpoint: Add a vote
@app.route('/vote', methods=['POST'])
def vote():
    """
    Endpoint to submit a new vote.

    Expects JSON data with 'voter_id' and 'candidate'.

    Returns:
    - JSON response with a success message or error.
    """
    data = request.get_json()
    voter_id = data.get('voter_id')
    candidate = data.get('candidate')
    if not voter_id or not candidate:
        return jsonify({"error": "Missing voter_id or candidate"}), 400
    try:
        index = blockchain.add_vote(voter_id, candidate)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({
        "message": f"Vote registered in block {index}!",
        "voter_id": voter_id,
        "candidate": candidate
    }), 201


@app.route('/mine', methods=['GET'])
def mine_block():
    """
    Endpoint to mine a new block containing pending votes.

    Returns:
    - JSON response with the details of the newly mined block or a message if no votes to mine.
    """
    if not blockchain.current_votes:
        return jsonify({"message": "No votes to mine."}), 200

    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    blockchain.broadcast_block(block)  # Broadcast only the new block
    return jsonify({
        "message": "New block mined successfully!",
        "index": block['index'],
        "timestamp": block['timestamp'],
        "votes": block['votes'],
        "proof": block['proof'],
        "previous_hash": block['previous_hash'],
        "hash": block['hash']
    }), 200


# Endpoint: Get the blockchain
@app.route('/chain', methods=['GET'])
def get_chain():
    """
    Endpoint to retrieve the entire blockchain.

    Returns:
    - JSON response with the blockchain, its length, and registered peers.
    """
    return jsonify({
        "chain": blockchain.chain,
        "length": len(blockchain.chain),
        "peers": list(blockchain.peers)  # Include peers in the response
    }), 200

# Endpoint: Validate the blockchain
@app.route('/validate', methods=['GET'])
def validate_chain():
    """
    Endpoint to validate the integrity of the blockchain.

    Returns:
    - JSON response indicating whether the blockchain is valid or invalid.
    """
    is_valid = blockchain.is_chain_valid()
    if is_valid:
        return jsonify({"message": "Blockchain is valid!"}), 200
    else:
        return jsonify({"message": "Blockchain is invalid!"}), 400

# Endpoint: Register a new peer
@app.route('/register_peer', methods=['POST'])
def register_peer():
    """
    Endpoint to register a new peer in the network.

    Expects JSON data with 'peer' (the address of the peer).

    Returns:
    - JSON response with a success message or error.
    """
    data = request.get_json()
    peer = data.get('peer')
    if not peer:
        return jsonify({"error": "Missing peer address"}), 400
    parsed_url = urlparse(peer)
    if parsed_url.netloc:
        blockchain.register_peer(peer)
        return jsonify({"message": f"Peer {peer} registered successfully."}), 201
    else:
        return jsonify({"error": "Invalid peer address"}), 400

# Endpoint: Receive chain from a peer
@app.route('/receive_chain', methods=['POST'])
def receive_chain():
    """
    Endpoint to receive the blockchain from a peer.

    Expects JSON data with 'chain'.

    Returns:
    - JSON response indicating whether the chain was updated or not.
    """
    data = request.get_json()
    incoming_chain = data.get('chain')
    if not incoming_chain:
        return jsonify({"error": "Missing chain data"}), 400
    if blockchain.is_chain_valid(incoming_chain) and len(incoming_chain) > len(blockchain.chain):
        blockchain.chain = incoming_chain
        blockchain.save_chain()
        return jsonify({"message": "Chain updated."}), 200
    else:
        return jsonify({"message": "Received chain is invalid or not longer."}), 400

# Endpoint: Consensus - resolve conflicts
@app.route('/consensus', methods=['GET'])
def consensus():
    """
    Endpoint to run the consensus algorithm and resolve any conflicts.

    Returns:
    - JSON response indicating whether the chain was replaced or is authoritative.
    """
    replaced = blockchain.resolve_conflicts()
    if replaced:
        return jsonify({"message": "Chain was replaced with the longer chain.", "new_chain": blockchain.chain}), 200
    else:
        return jsonify({"message": "Our chain is authoritative.", "chain": blockchain.chain}), 200

# Endpoint: Check chain status
@app.route('/chain_status', methods=['GET'])
def chain_status():
    """
    Endpoint to check the current status of the blockchain.

    Returns:
    - JSON response indicating whether the chain is valid and a corresponding message.
    """
    return jsonify({
        "is_valid": blockchain.is_valid,
        "message": "Chain is valid." if blockchain.is_valid else "Chain is invalid."
    }), 200

# Endpoint: Reset the blockchain to the genesis block
@app.route('/reset_chain', methods=['POST'])
def reset_chain():
    """
    Endpoint to reset the blockchain to the genesis block.

    Returns:
    - JSON response indicating the result of the reset operation.
    """
    # Only allow resetting if the chain is invalid
    if blockchain.is_valid:
        return jsonify({"message": "Chain is already valid. No need to reset."}), 400

    blockchain.chain = []
    blockchain.current_votes = []
    blockchain.create_block(proof=1, previous_hash='0')
    blockchain.is_valid = True  # Reset the validity flag
    return jsonify({"message": "Blockchain has been reset to the genesis block."}), 200


@app.route('/receive_block', methods=['POST'])
def receive_block():
    """
    Endpoint to receive a new block from a peer.

    Expects JSON data with 'block'.

    Returns:
    - JSON response indicating whether the block was added or rejected.
    """
    data = request.get_json()
    incoming_block = data.get('block')

    if not incoming_block:
        return jsonify({"error": "Missing block data"}), 400

    # Get the last block in the current chain
    last_block = blockchain.get_previous_block()

    # Validate the incoming block
    if last_block['hash'] != incoming_block['previous_hash']:
        return jsonify({"error": "Previous hash does not match."}), 400

    if not blockchain.is_valid_proof(last_block['proof'], incoming_block['proof']):
        return jsonify({"error": "Invalid proof of work."}), 400

    # Add the new block to the chain
    blockchain.chain.append(incoming_block)
    blockchain.save_chain()
    return jsonify({"message": "Block added to the chain."}), 200


# Endpoint: Serve the frontend page
@app.route('/')
def index():
    """
    Endpoint to serve the frontend HTML page.

    Returns:
    - Rendered 'index.html' template.
    """
    return render_template('index.html')

# Run the app
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default=5555, type=int, help='Port to run the server on')
    args = parser.parse_args()
    port = args.port

    app.run(debug=True, port=port)
