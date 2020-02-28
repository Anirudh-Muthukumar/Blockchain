
from blockchain import *
import random

random.seed(500) # for reproducible results

def MineBlock(chain, parent, target, txs=None):
    """Helper function for the Test, that mines a block"""
    assert(type(chain) is Blockchain)
    assert(type(parent) is int)
    assert(type(target) is int)
    b = Block()
    b.setPriorBlockHash(parent)
    b.setContents(txs)
    b.mine(target)
    if not chain.extend(b): return None
    # print("Chain extended!!!")
    return b

def TestMerkleTree():

    class hInt:
        def __init__(self, val):
            self.data = val
        def getHash(self):
            msg = hashlib.sha256()
            msg.update(self.data.to_bytes(32,"big"))
            return int.from_bytes(msg.digest(),"big")

    assert(HashableMerkleTree([]).calcMerkleRoot().to_bytes(32,"big").hex() == "0000000000000000000000000000000000000000000000000000000000000000")
    assert(HashableMerkleTree([hInt(x) for x in [1]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ec4916dd28fc4c10d78e287ca5d9cc51ee1ae73cbfde08c6b37324cbfaac8bc5")
    assert(HashableMerkleTree([hInt(x) for x in [2]]).calcMerkleRoot().to_bytes(32,"big").hex() == "9267d3dbed802941483f1afa2a6bc68de5f653128aca9bf1461c5d0a3ad36ed2")
    assert(HashableMerkleTree([hInt(x) for x in [1,2]]).calcMerkleRoot().to_bytes(32,"big").hex() == "56af8f5d76765ecd266c7bbc471280f0b5962cab703465e0d9d06932fa47b782")
    assert(HashableMerkleTree([hInt(x) for x in [1,2,3]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ea670d796aa1f950025c4d9e7caf6b92a5c56ebeb37b95b072ca92bc99011c20")
    assert(HashableMerkleTree([hInt(x) for x in [1,2,3,4]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ac82b024e679779e3372fbb95447bb318afa87e1e53783fdfdd9de61257638ff")


def MakeUtxoFrom(txes):
    if not type(txes) is list:
        txes = [txes]
    ret = {}
    for tx in txes:
        idx = 0
        for out in tx.outputs:
            ret[(tx.getHash(),idx)] = out
            idx += 1
    return ret

def TestTransactionGraph():
    t0 = Transaction(None, [Output(lambda x: True, 30), Output(lambda x: True, 20)])
    # minted too many
    assert(not t0.validateMint(20))
    # minted less
    assert(t0.validateMint(100))
    # minted exact amount
    assert(t0.validateMint(50))

    t1 = Transaction([Input(t0.getHash(), 0, [])], [Output(lambda x: x[0] == "alice", 10), Output(lambda x: x[0] == "bob", 20)])

    assert(t1.validate(MakeUtxoFrom(t0)) == True)

    txes = MakeUtxoFrom([t0,t1])

    # the parameter [1] won't meet the constraint that this parameter is ["alice"]
    t2 = Transaction([Input(t1.getHash(),0,[1])], [Output(lambda x: True,5)])
    assert(t2.validate(txes) == False)

    # the parameter is correct so this will work
    t2 = Transaction([Input(t1.getHash(),0,["alice"])], [Output(lambda x: x[0] == "carol",5)])
    assert(t2.validate(txes) == True)

    txes.update(MakeUtxoFrom(t2))

    # send too much value compared to what was input
    t3 = Transaction([Input(t2.getHash(),0,["carol"])], [Output(lambda x: True,6)])
    assert(t3.validate(txes) == False)

    # Send the right amount
    t3 = Transaction([Input(t2.getHash(),0,["carol"])], [Output(lambda x: True,5)])
    assert(t3.validate(txes) == True)

    # Send less (miner gets the extra as fees)
    t3 = Transaction([Input(t2.getHash(),0,["carol"])], [Output(lambda x: True,4)])
    assert(t3.validate(txes) == True)

def TestBlocks():
    b = Block()
    print (b.getHash())
    b.mine(int("F"*64,16))
    print("%x" % b.getHash())
    b.mine(int("F"*63,16))
    print("%x" % b.getHash())
    b.mine(int("F"*60,16))
    print("%x" % b.getHash())

def TestBlockchainOnly():
    # create a chain with initial difficulty
    chain = Blockchain(int("4" + ("F"*63),16), 50)

    # T1: check that the genesis block difficulty is what I asked for
    tip = chain.getTip()
    assert(tip.target == int("4" + ("F"*63),16))

    # T2: check that there's only one genesis block
    tip2 = chain.getBlocksAtHeight(0)
    assert(len(tip2) == 1)
    # T3: and that getBlocksAtHeight serves the correct block
    assert(tip.getHash() == tip2[0].getHash())


    # mine a block and see if its on the tip
    tgt = int("1" + ("F"*63),16)
    forkTipHash = tip.getHash()
    b = Block()
    b.setPriorBlockHash(forkTipHash)
    b.mine(tgt)
    chain.extend(b)

    tip = chain.getTip()
    # T4: Did this new block get on the tip?
    assert(tip.getHash() == b.getHash())
    # T5: Was a block of the right difficulty mined?
    assert(tip.getHash() <= tgt)


    # Mine a block disconnected from the blockchain
    b = MineBlock(chain, 1234, tgt)
    assert(b == None)


    # Mine a block at lower difficulty
    b = MineBlock(chain, forkTipHash, tgt*4)
    tip2 = chain.getTip()
    # T6: Tip should not change because this fork's work is less
    assert(tip2.getHash() == tip.getHash())

    
    # Make a longer chain at lower difficulty
    b = MineBlock(chain, b.getHash(), tgt*4)
    lessTipHash = b.getHash()

    # T7: Tip should not change because this fork's work is less
    assert(chain.getTip().getHash() == tip.getHash())


    # Mine higher work block to change the tip
    b = MineBlock(chain, lessTipHash, tgt)
    # Tip should now change
    tip3 = chain.getTip()
    assert(tip3.getHash() == b.getHash())

    # Mine another block so this tip is far ahead of the other
    b = MineBlock(chain, b.getHash(), tgt)


    # Mine a high difficulty block so this shorter tip wins
    b = MineBlock(chain, tip.getHash(), int(tgt/8))

    assert(b.getHash() == chain.getTip().getHash())


def TestBlockchainWithTransactions():
    # create a chain with initial difficulty
    chain = Blockchain(int("4" + ("F"*63),16), 50)

    tgt = int("1" + ("F"*63),16)

    tip = chain.getTip()
    
    # mint too many coins for this chain
    b = MineBlock(chain, tip.getHash(), tgt, [ Transaction(None, [Output(lambda x: True, 60)])])
    assert(b == None)
    # print("\nTC 1 passed!!!\n")

    # A good block
    tx0 = Transaction(None, [Output(lambda x: True, 50)])
    g = MineBlock(chain, tip.getHash(), tgt, [ tx0 ])
    assert(g != None)
    # print("\nTC 2 passed!!!\n")

    tip = chain.getTip()
    assert(tip == g)
    # print("\nTC 3 passed!!!\n")

    # mint transaction is not first
    b = MineBlock(chain, tip.getHash(), tgt, [ Transaction([Input(g.getHash(),0,[])], [Output(lambda x: x[0] + x[1] == 100)]), Transaction(None, [Output(lambda x: True, 50)]) ])
    assert(b == None)
    assert(chain.getTip() == tip)
    # print("\nTC 4 passed!!!\n")

    # double mint transaction
    b = MineBlock(chain, tip.getHash(), tgt, [ Transaction(None, [Output(lambda x: True, 50)]), Transaction(None, [Output(lambda x: True, 50)]) ])
    assert(b == None)
    assert(chain.getTip() == tip)
    # print("\nTC 5 passed!!!\n")

    # chain.displayChain()

    # bogus prior input hash
    b = MineBlock(chain, tip.getHash(), tgt, [ Transaction(None, [Output(lambda x: True, 50)]), Transaction([Input(g.getHash(),0,[])], [Output(lambda x: x[0] + x[1] == 100)])  ])
    assert(b == None)
    assert(chain.getTip() == tip)
    # print("\nTC 6 passed!!!\n")

    # bogus prior input index
    b = MineBlock(chain, tip.getHash(), tgt, [ Transaction(None, [Output(lambda x: True, 50)]), Transaction([Input(tx0.getHash(),1,[])], [Output(lambda x: x[0] + x[1] == 100)])  ])
    assert(b == None)
    assert(chain.getTip() == tip)
    # print("\nTC 7 passed!!!\n")


    # ok
    tx2 = Transaction([Input(tx0.getHash(),0,[])], [Output(lambda x: x[0] + x[1] == 100, 49)])
    tx1 = Transaction(None, [Output(lambda x: True, 50)], "uniquifer1")
    b = MineBlock(chain, tip.getHash(), tgt, [ tx1, tx2])
    assert(b != None)
    assert(chain.getTip() == b)
    # print("\nTC 8 passed!!!\n")


    # bad input constraint, doesn't add up   -> wrong tip passed??? coz tx1 is present in block A2 not A1
    tx3 = Transaction([Input(tx1.getHash(),0,[]), Input(tx2.getHash(),0, [ 25, 79])], [Output(lambda x: hashlib.sha256(x[0]).digest().hex() == '172aea8425ac5db48bb2363e13a7443f5aa5e1e0cad30d943398ff18d5f904f2', 99)])
    tx4 = Transaction(None, [Output(lambda x: True, 49)])
    b = MineBlock(chain, tip.getHash(), tgt, [ tx4, tx3 ])
    assert(b == None)
    # print("\nTC 9 passed!!!\n")

    # these tx are not valid on this tip
    tx3 = Transaction([Input(tx1.getHash(),0,[]), Input(tx2.getHash(),0, [ 25, 75])], [Output(lambda x: hashlib.sha256(x[0]).digest().hex() == '172aea8425ac5db48bb2363e13a7443f5aa5e1e0cad30d943398ff18d5f904f2', 99)])
    tx4 = Transaction(None, [Output(lambda x: True, 49)])
    b = MineBlock(chain, tip.getHash(), tgt, [ tx4, tx3 ])
    assert(b == None)
    # print("\nTC 10 passed!!!\n")

    # chain.displayChain()
    # print("Chain tip: ", chain.getTip().getHash())
    # ok, run those tx on the proper tip.
    tip = chain.getTip()
    b = MineBlock(chain, tip.getHash(), tgt, [ tx4, tx3 ])
    assert(b != None)
    assert(chain.getTip() == b)
    # print("\nTC 11 passed!!!\n")


    burnMint = Transaction(None, [Output(lambda x: False, 0)])

    # bad input index
    tx5 = Transaction([Input(tx3.getHash(),4,[b"preimage secret 1"])], [ Output(lambda x: True, 50), Output(lambda x: False, 10), Output(lambda x: True, 38) ])
    b = MineBlock(chain, chain.getTip().getHash(), int(tgt/2), [ burnMint, tx5])
    assert( b == None)
    # print("\nTC 12 passed!!!\n")

    # chain.displayChain()
    # print("Chain tip: ", chain.getTip().getHash())
    # print() 

    # bad satisfier
    tx5 = Transaction([Input(tx3.getHash(),0,[b"bad secret"])], [ Output(lambda x: True, 50), Output(lambda x: False, 10), Output(lambda x: True, 38) ])
    b = MineBlock(chain, chain.getTip().getHash(), int(tgt/2), [ burnMint, tx5])
    assert( b == None)
    # print("\nTC 13 passed!!!\n")

    # ok input index is correct
    tx5 = Transaction([Input(tx3.getHash(),0,[b"preimage secret 1"])], [ Output(lambda x: True, 50), Output(lambda x: False, 10), Output(lambda x: True, 38) ])
    b = MineBlock(chain, chain.getTip().getHash(), int(tgt/2), [ burnMint, tx5])
    assert( b != None)
    # print("\nTC 14 passed!!!\n")
    
    
    
def Test():
    TestBlocks() # completed
    TestMerkleTree() # completed
    TestTransactionGraph() # completed 
    TestBlockchainOnly() # completed
    TestBlockchainWithTransactions() # completed

if __name__ == "__main__":
    Test()
