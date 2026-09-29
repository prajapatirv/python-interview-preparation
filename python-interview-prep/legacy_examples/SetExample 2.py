"""
created by {val1,val2,.....valn}
It maintain unique values with no order
Set does not work on index
Can't access data on index(TypeError: 'set' object is not subscriptable)
Can't modify data on index (TypeError: 'set' object does not support item assignment)

"""
from mysqlx import Compression

my_Set={12,34,56,78,90,100,12,34,56,12}
print(type(my_Set))
print("Set Elements:",my_Set)
# TypeError: 'set' object is not subscriptable
# print(my_Set[2])

# TypeError: 'set' object does not support item assignment
# my_Set[2]=500


# Dynamic Set
# set1=set(map(int,input("Enter Set Elements:").split(",")))
# print("Set Elements:",set1)
# print(type(set1))
#
# # Write code find cube of each element of dynamic set
# #create empty set to hold cube of each element
# cube=set()# Empty set
# print(type(cube))
# for val in set1:
#     # print(val*val*val)
#     cube.add(val*val*val)
#
# print(cube)


# Code Compression
# set1=set(map(int,input("Enter Set Elements:").split(",")))
# print("Set Elements:",set1)
# # Write code find cube of each element of dynamic set
# #create empty set to hold cube of each element
# my_cubes={val*val*val for val in set1}
# print(my_cubes)


# Find square of even numbers of Dynamic list and add it in new set
# my_set=set(map(int,input("Enter Set Elements:").split(" ")))
# # even_num_sq=set() # empty set
# # for val in my_set:
# #     if val%2==0:
# #         even_num_sq.add(val*val)
#
# even_num_sq={ val*val for val in my_set if val%2==0}
# print("Square of even numbers:",even_num_sq)
# print(type(even_num_sq))

#From List Find odd numbers from set and push its 4th power into new list


# Set Methods
"""
update(iterable):Add multiple elements from another iterable
"""

set1={1,2,3,4}
set2=[8,9,10,11]
set1.update(set2)
print(set1)
print(type(set1))

"""
remove(object):-It will remove given object 
If given object is not exist it will generate exception KeyError
"""
set1.remove(11)
print(set1)

"""
discard(Object):It will remove given object but ot will not generate any error if object is not exist
"""
set1.discard(80)
print(set1)

"""
pop():-Removes and return an arbitrary element
clear():- Remove all elements 
"""

print(set1.pop())
print(set1)

print(set1.pop())
print(set1)

set1.clear()
print(set1)

# Operators from set
"""
union(set):-return all elements from both sets
&
intersection(set):-return only common elements from both sets
difference(set):-return elements from current set which are not part of given set
or
"""
set3={1,2,3,4,5,6}
set4={4,5,6,7,8,9}
print("union:",set3.union(set4))
print("union(|):",set3|set4)

print("intersection:",set3.intersection(set4))
print("intersection(&):",set3 & set4)

print("difference:",set3.difference(set4))
print("difference(-):",set3-set4)
















