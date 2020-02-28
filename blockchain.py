"""
In this assignment you will extend and implement a class framework to create a simple but functional blockchain that combines the ideas of proof-of-work, transactions, blocks, and blockchains.
You may create new member functions, but DO NOT MODIFY any existing APIs.  These are the interface into your blockchain.

Many functions are not implemented -- they just call "pass".  You need to implement them.

This blockchain has the following consensus rules (it is a little different from Bitcoin to make testing easier):

Blockchain

1. There are no consensus rules pertaining to the minimum proof-of-work of any blocks.  That is it has no "difficulty adjustment algorithm".
Instead, your code will be expected to properly place blocks of different difficulty into the correct place in the blockchain and discover the most-work tip.

2. A block with no transactions whatsoever is valid (this will help us isolate tests).

3. Only the first transaction in a block can be a mint transaction (coinbase in Bitcoin vocabulary), and that first transaction MUST be a mint transaction.

Block Merkle Tree

1. You must use sha256 hash 
2. You must use 0 if additional items are needed to pad odd merkle levels
(more specific information is included below)

Transactions

1. A transaction with inputs==None is a valid mint (coinbase) transaction.  The coins created must not exceed the per-block "minting" maximum.

2. If the transaction is not a mint transaction, coins cannot be created.  In other words, coins spent (inputs) must be >= coins sent (outputs).

3. Constraint scripts (permission to spend) are implemented via python lambda expressions (anonymous functions).  These constraint scripts must accept a list of parameters, and return True if
   permission to spend is granted.  If execution of the constraint script throws an exception or returns anything except True do not allow spending!



"""

import hashlib
import pdb
import copy
import json
import pickle
import random
from collections import defaultdict

# pip3 install dill
import dill

class Output:
    """ This models a transaction output """
    def __init__(self, constraint = None, amount = 0):
        """ constraint is a function that takes 1 argument which is a list of 
            objects and returns True if the output can be spent.  For example:
            Allow spending without any constraints (the "satisfier" in the Input object can be anything)
            lambda x: True

            Allow spending if the spender can add to 100 (example: satisfier = [40,60]):
            lambda x: x[0] + x[1] == 100

            If the constraint function throws an exception, do not allow spending.
            For example, if the satisfier = ["a","b"] was passed to the previous constraint script

            If the constraint is None, then allow spending without constraint

            amount is the quantity of tokens associated with this output """
        if constraint == None:
            self.constraint = lambda x: True
        else:
            self.constraint = constraint
        self.amount = amount
        assert(type(self.amount) == int)

class Input:
    """ This models an input (what is being spent) to a blockchain transaction """
    def __init__(self, txHash, txIdx, satisfier):
        """ This input references a prior output by txHash and txIdx.
            txHash is therefore the prior transaction hash
            txIdx identifies which output in that prior transaction is being spent.  It is a 0-based index.
            satisfier is a list of objects that is be passed to the Output constraint script to prove that the output is spendable.
        """
        self.txHash = txHash
        self.txIdx = txIdx
        self.satisfier = satisfier
        assert(type(self.txHash) == int)
        assert(type(self.txIdx) == int)
        assert(type(self.satisfier) == list)

class Transaction:
    """ This is a blockchain transaction """
    def __init__(self, inputs=None, outputs=None, data = None):
        """ Initialize a transaction from the provided parameters.
            inputs is a list of Input objects that refer to unspent outputs.
            outputs is a list of Output objects.
            data is a byte array to let the transaction creator put some 
              arbitrary info in their transaction.
        """
        if inputs == None:
            self.inputs = []
        else:
            self.inputs = inputs

        if outputs == None:
            self.outputs = []
        else:
            self.outputs = outputs

        #  fill in the rest of the method

        self.data = data   # to store arbitrary data 

    def getHash(self):
        """Return this transaction's probabilistically unique identifier as an integer"""
        # should return object's sha256 hash as a big endian integer

        # considering txHash, txIdx of Inputs and amount from Outputs for creating the transaction hash
        msg = hashlib.sha256();

        if len(self.inputs) > 0:
            for input in self.inputs:
                msg.update(input.txHash.to_bytes(32,"big"))
                msg.update(input.txIdx.to_bytes(32,"big"))
        
        if len(self.outputs) > 0:
            for output in self.outputs:
                msg.update(output.amount.to_bytes(32,"big"))
        
        return int.from_bytes(msg.digest(),"big")

    def getInputs(self):
        """ return a list of all inputs that are being spent """
        return self.inputs

    def getOutput(self, n):
        """ Return the output at a particular index """
        return self.outputs[n-1]


    def validateMint(self, maxCoinsToCreate):
        """ Validate a mint (coin creation) transaction.
            A coin creation transaction should have no inputs,
            and the sum of the coins it creates must be less than maxCoinsToCreate.
        """
        if len(self.inputs) != 0:
            print("mint tx has inputs")
            return False
        # check output amounts
        outAmount = 0
        for out in self.outputs:
            outAmount += out.amount
        if maxCoinsToCreate < outAmount:  # Oops spent too much!
            return False
        return True

    def validate(self, unspentOutputDict):
        """ Validate this transaction given a dictionary of unspent transaction outputs.
            unspentOutputDict is a dictionary of items of the following format: { (txHash, offset) : Output }
            Return True if this transaction is valid, or False.
        """
        
        # two conditions: 
        # 1. Income >= Expenses 
        # 2. All the inputs should be part of unspentOutputDict

        totalIncome, totalExpenses = 0, 0
        
        for output in self.outputs:
            totalExpenses += output.amount 

        # print("UTXO : ")
        # for key, val in unspentOutputDict.items():
        #     print(key, val)
        # print()

        for i in range(len(self.inputs)):
            input = self.inputs[i]
            txHash = input.txHash
            txIdx = input.txIdx
            if (txHash, txIdx) not in unspentOutputDict: # bogus input hash
                # print("Bogus input hash")
                return False 
            unspentOutput = unspentOutputDict[(txHash, txIdx)]
            if input.satisfier==[] or unspentOutput.constraint(input.satisfier): # if constraint is satisfied alone spend the output
                totalIncome += unspentOutput.amount
            else:
                return False
        
        # Expenses should always be less than or equal to income
        return totalIncome >= totalExpenses


class HashableMerkleTree:
    """ A merkle tree of hashable objects.

        If no transaction or leaf exists, use 32 bytes of 0.
        The list of objects that are passed must have a member function named
        .getHash() that returns the object's sha256 hash as an big endian integer.

        Your merkle tree must use sha256 as your hash algorithm and big endian
        conversion to integers so that the tree root is the same for everybody.
        This will make it easy to test.

        If a level has an odd number of elements, append a 0 value element.
        if the merkle tree has no elements, return 0.

    """

    def __init__(self, hashableList = None):
        if hashableList == None:
            self.hashables = []
        else:
            self.hashables = hashableList

    def calcMerkleRoot(self):
        """ Calculate the merkle root of this tree."""

        # Hard code the degenerate case
        if len(self.hashables)==0:
            return 0
        
        leafNodes = []
        
        for i in range(len(self.hashables)):
            leafNodes.append(self.hashables[i].getHash())
        
        while len(leafNodes) > 1:
            newLeaves = []

            if len(leafNodes)%2!=0:  # adding 0 to levels with odd # of elements
                # zero = 0
                leafNodes.append(0)

            for i in range(0, len(leafNodes), 2):
                hxy = leafNodes[i].to_bytes(32, "big") + leafNodes[i+1].to_bytes(32, "big")
                msg = hashlib.sha256()
                msg.update(hxy)
                newLeaves.append(int.from_bytes(msg.digest(), "big"))
            
            leafNodes = newLeaves

        return leafNodes[0]


class BlockContents:
    """ The contents of the block (merkle tree of transactions)
        This class isn't really needed.  I added it so the project could be cut into
        just the blockchain logic, and the blockchain + transaction logic.
    """
    def __init__(self):
        self.data = HashableMerkleTree()

    def setData(self, d):
        self.data = d

    def getData(self):
        return self.data

    def calcMerkleRoot(self):
        return self.data.calcMerkleRoot()

class Block:
    """ This class should represent a blockchain block.
        It should have the normal fields needed in a block and also an instance of "BlockContents"
        where we will store a merkle tree of transactions.
    """
    def __init__(self):
        # Hint, beyond the normal block header fields what extra data can you keep track of per block to make implementing other APIs easier?

        # immutable values
        self.version = 0 # block version initialized to 0
        self.parentBlockHash = 0 # hash of previous block 
        self.target = 8 # target or difficulty

        # mutable values
        self.blockContents = BlockContents() # merkle root of all transactions 
        self.time = 3 # timestamp
        self.nonce = 1 # block nonce value 

        # extra value to make API implementation easier????
        self.children = []
        self.cumulativeWork = 0
        self.height = 0

    def getContents(self):
        """ Return the BlockContents """
        return self.blockContents.getData()

    def setContents(self, data):
        """ set the contents of this block's merkle tree (inside BlockContents) to the list of objects in the data parameter """
        self.blockContents.setData(data) 

    def setTarget(self, target):
        """ Set the difficulty target of this block """
        self.target = target

    def getTarget(self):
        """ Return the difficulty target of this block """
        return self.target

    def getHash(self):
        """ Calculate the hash of this block. Return as an integer """
        # using following attributes to find the block hash
        # version, priorBlockHash, target, time and nonce
        blockHash = hashlib.sha256()
        blockHash.update(self.version.to_bytes(32,"big"))
        blockHash.update(self.parentBlockHash.to_bytes(32,"big"))
        blockHash.update(self.target.to_bytes(32,"big"))
        blockHash.update(self.time.to_bytes(32,"big"))
        blockHash.update(self.nonce.to_bytes(32,"big"))

        return int.from_bytes(blockHash.digest(),"big")

    def setPriorBlockHash(self, priorHash):
        """ Assign the parent block hash """
        self.parentBlockHash = priorHash

    def getPriorBlockHash(self):
        """ Return the parent block hash """
        return self.parentBlockHash

    def mine(self,tgt):
        """Modify this block until its hash is less than the passed target tgt"""
        self.target = tgt

        blockHash = self.getHash()
        ct = 1

        # keep changing nonce value until blockHash is less than or equal to target
        while blockHash > tgt:
            self.nonce += random.randint(1, 2**64) # pick a random integer between 0 and 2^64
            blockHash = self.getHash()
            # print("Try %d" %(ct))
            ct += 1
        
        # print("Mined the block with nonce = %d" %(self.nonce))


    def validate(self, unspentOutputs, maxMint):
        """ Given a dictionary of unspent outputs, and the maximum amount of
            coins that this block can create, determine whether this block is valid.
            Return None if the block is invalid.

            Return something else if the block is valid 

            HINT: you may want to return a new unspent output object with the transactions in this
            block applied, for your own use when implementing other APIs.
        """
        # First transaction in the block should be coinbase transaction 
        # coinbase transaction should be less than or equal to maxMint 
        # input transactions are from unspent transactions 
        
        if type(self.blockContents.getData())!=HashableMerkleTree():
            blockTransactions = self.blockContents.getData()
            # print("# of txns in block: ", len(blockTransactions))
            coinbaseTransaction = blockTransactions[0]
            mintAmount = coinbaseTransaction.outputs[0].amount 
            # print("Coinbase Transaction : ", coinbaseTransaction)

            if coinbaseTransaction.inputs != [] or mintAmount > maxMint: # input of coinbase transaction should be None 
                # print("Mint amount error")
                return False 
            
            for i in range(1, len(blockTransactions)):
                transaction = blockTransactions[i]
                if transaction.inputs==[]: # double mint transaction 
                    return False

                # validate the current transaction using Transaction.validate(UtxO)
                if not transaction.validate(unspentOutputs):
                    return False 

                for input in transaction.inputs:
                    if (input.txHash, input.txIdx) not in unspentOutputs:  # check for bogus transaction inputs
                        # print("Bogus Input error for txn %d\n" %(i+1))
                        return False 

                    
        return True 


class Blockchain(object):

    def __init__(self, genesisTarget, maxMintCoinsPerTx):
        """ Initialize a new blockchain and create a genesis block.
            genesisTarget is the difficulty target of the genesis block (that you should create as part of this initialization).
            maxMintCoinsPerTx is a consensus parameter -- don't let any block into the chain that creates more coins than this!
        """
        self.genesisTarget = genesisTarget
        self.maxMintCoinsPerTx = maxMintCoinsPerTx
        # create a data structure of blocks to maintain the chain
        self.chain = []
        self.blockChain = defaultdict(list)
        genesisBlock = Block()  # creating a genesis block
        genesisBlock.setTarget(genesisTarget)   # set the difficulty of the genesis block
        genesisBlock.cumulativeWork = 1   # work of genesis block is 1
        self.chain.append(genesisBlock)    # add genesis block to the chain
        self.root = genesisBlock
        self.blockHashMapping = defaultdict(Block)  # mapping between block hash and the block
        self.blockHashMapping[self.root.getHash()] = self.root

        # pointer to chain tip and attribute which keeps track of maximum Work of any fork
        self.chainTip = self.root
        self.maxWork = self.root.cumulativeWork  
        
    def getTip(self):
        """ Return the block at the tip (end) of the blockchain fork that has the largest amount of work"""
        return self.chainTip

    def getWork(self, target):
        """Get the "work" needed for this target.  Work is the ratio of the genesis target to the passed target"""
        # print("GT ", self.genesisTarget)
        # print("PT ", target)
        return self.genesisTarget/target

    def getCumulativeWork(self, blkHash):
        """Return the cumulative work for the block identified by the passed hash.  Return None if the block is not in the blockchain"""

        if blkHash not in self.blockHashMapping: # block is not present in Blockchain
            return None 
        
        return self.blockHashMapping[blkHash].cumulativeWork
        

    def getBlocksAtHeight(self, height):
        """Return an array of all blocks in the blockchain at the passed height (including all forks)"""
        
        arrayOfBlocks = []

        for blockHash, block in self.blockHashMapping.items():
            if block.height==height:
                arrayOfBlocks.append(block)
        
        return arrayOfBlocks

    def extend(self, block):
        """Adds this block into the blockchain in the proper location.
           Return false if the block is invalid (breaks any miner constraints), and do not add it to the blockchain."""

        # find the parent block of given block
        if block.parentBlockHash not in self.blockHashMapping:
            return False 
        
        # print("Block %s contents = %s" %(block.getHash(), block.getContents()))
        blockContents = block.getContents()
        # print(type(blockContents))
        parent = self.blockHashMapping[block.parentBlockHash]
        
        # validate blocks which have transactions, essentially used for TestBlockchainWithTransactions()
        if blockContents != None and type(blockContents)!=type(HashableMerkleTree()):
            
            # print("# of ancestors for block %s: " %(block.getHash()))
            unspentOutputs = self.findUnspentOutputs(parent)
            
            # print("Length of unspent outputs :", len(unspentOutputs))

            if not block.validate(unspentOutputs, self.maxMintCoinsPerTx):
                return False

        # update the "children" attribute of parent block
        parent.children.append(block) 

        # compute to cumulative work of the block as sum of its work plus cumulative work of its parent
        block.cumulativeWork = self.getWork(block.target) + parent.cumulativeWork

        # update the chain tip
        if block.cumulativeWork > self.maxWork:
            self.chainTip = block
            self.maxWork = block.cumulativeWork

        # update blockHashMapping 
        self.blockHashMapping[block.getHash()] = block 

        # update the height of the block 
        block.height = parent.height + 1

        
        # create a directed edge from parent to child - we can always access the parent of given through parentBlockHash of child
        self.blockChain[parent].append(block)

        return True # block is successfully added
    
    def findUnspentOutputs(self, tempBlock):
        temp = tempBlock
        ancestors = []

        # Traverse until the genesis block through priorBlockHash
        while temp.getHash() != self.root.getHash():
            ancestors.append(temp)
            temp = self.blockHashMapping[temp.parentBlockHash]
        
        # Add genesis block as well 
        # ancestors.append(self.root)  ->>>>> chuck genesis block for a while
        
        # Length of ancestors
        # print("Ancestors for block: ", len(ancestors))

        unspent = defaultdict(int)
        
        # genesisTransactions = ancestors[-1].getContents()

        # if type(genesisTransactions)!=type([]):
        #     print("Stuck hereee")
        #     return dict()

        # for txn in genesisTransactions:
        #     idx = 0
        #     for output in txn.outputs:
        #         unspent[(txn.getHash(), idx)] = output
        #         idx += 1

        outputs = []

        for i in range(len(ancestors)-1, -1, -1): # from genesis to parent block
            block = ancestors[i]
            blockTxns = block.getContents()
            # print("\n# of txns in block : ", len(blockTxns))
            # for txn in blockTxns:
            #     for input in txn.inputs:
            #         if (input.txHash, tx.txIdx) in unspent: # delete spent outputs
            #             del unspent[(input.txHash, tx.txIdx)]

                # add outputs to unspent pool of transactions
            for txn in blockTxns:
                idx = 0
                for output in txn.outputs:
                    unspent[(txn.getHash(), idx)] = output
                    idx += 1
        
        # print("\nUnspent Transactions: ", unspent)
        # print()
        # print()
        return unspent

    def displayChain(self):
        print()
        print("Cumulative Work: ")
        for blockHash, block in self.blockHashMapping.items():
            print(blockHash, block.cumulativeWork)
        print()
        


