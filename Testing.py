import hashlib
# print()
# print()
# gb = int("4" + ("F"*63),16)
# a1 = int("1" + ("F"*63),16)
# print("GB target: ", gb)

# print("A1 target: ", a1)

# print("A1 work: ", gb/a1)
# print([b"preimage secret 1"])

print(hashlib.sha256(b"preimage secret 1").digest().hex() == '172aea8425ac5db48bb2363e13a7443f5aa5e1e0cad30d943398ff18d5f904f2')

print()