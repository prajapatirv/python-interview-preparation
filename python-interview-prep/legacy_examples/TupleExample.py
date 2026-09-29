"""
tuple
created using ()
stores duplicate data
preserve insertion order
Support indexing
can access data on index
We cant modify value on the basis of index:-TypeError: 'tuple' object does not support item assignment
immutable
not growable
"""
my_tuple=(1,2,3,4,1,2,3,4,4)
print(type(my_tuple))
print(my_tuple)
print("Element from 3rd index:",my_tuple[3])
# my_tuple[3]=400
# print("Updated Tuple Elements:",my_tuple)
print("Count of 4:",my_tuple.count(4))
# append()/remove()/sort()-not supported by tuple as it is not modifiable

