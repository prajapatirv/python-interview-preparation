# """
# List:-
# created with [val1,val2,val3.....]
# It holds data with different data types
# Can hold duplicate data and maintain insertion order
# list can grow
# List works with index -start with zero
# Can access value on the basis of index
# can modify value on the basis of index(item assignment is supported in List)
# List is mutable
# """
#
# my_list=[12,34,56,78.90,"Sonali","Niteen",True,30+10j,12,78.90,12]
#
# print(type(my_list))
# print("List Elements:",my_list)
# """
# append(object):-
#     add given object at the end of current list
# """
# my_list.append("Ashish")
# print("List Elements after append:",my_list)
#
# print("Data from index:4th is:",my_list[4])
# my_list[4]="Omkar"
# print("List elements after modification is:",my_list)
#
# """
# Methods from List
# insert(position,object):-
#     It insert given object at given position
# """
# my_list.insert(4,"Kirti")
# print("List elements after insert:",my_list)
#
#
# """
# remove(object):-
#     remove given object from current string
#     Notes:-If given object is not exist in current List it will generate Exception :-ValueError
# """
# my_list.remove("Omkar")
# print("List elements after remove:",my_list)
#
# """
# reverse():-reverse current list elements
# """
# my_list.reverse()
# print("Reverse List:",my_list)
#
# list1=[23,1,45,100,2000,4000,1,23,1]
# print("List before sorting:",list1)
#
# """
# sort():-sort current List elements in
# """
# list1.sort()
# print("Sorted List :",list1)
#
# """
# count(Object):--it will return count of given object from current List
# """
# print("Count of 1:",list1.count(1))
#
# """
# index(Object):-It will return index of given object from current string
#             It implicitly return index of occurrence
# index(Object,start_index)
#
# """
# print("Index of 'Omkar':",my_list.index("Niteen"))
# print("Index of '12':",my_list.index(12))# 1,3,13
# print("Index of '12':",my_list.index(12,2))# 1,3,11
#
#
# """
# pop(index):-
#     remove data from given index and return same as output
#     If given index is not exist it generate Exception:-IndexError
# """
# print("Pop Method-'Niteen':",my_list.pop(6))
# print("After Pop:",my_list)
# """
# Functions:-
# max()
# """
#
# print("Max number:",max(list1))
# print("Nin Number:",min(list1))
# print("Sum:",sum(list1))
# print("Length:",len(my_list))

# Dynamic values in List

"""
map(operation,iterable)
split()
"""
# Iterable object
# my_list=[1,2,3,4]
# # sq_list=[]
# # Operation
# def sq(no):
#     return no*no
#
# # for val in list:
# #     result=sq(val)
# #     sq_list.append(result)
#
# sq_list=list(map(sq,my_list))
#
#
# print(sq_list)



"""
--read data from user:--input("message"):---it will read data in str type

my_list=input("Enter List elements:")--single string

***************Create Iterable object
input("Enter List elements:").split(" ")---list but each elements is of type string

**********Operation
Convert each element of Iterable object into int type--int()

To operate (int operation)on each element of Iterable object :--map()--return Map Object

Convert it into List:--list()

"""

my_list=list(map(int,input("Enter List elements:").split(" ")))
print(type(my_list))
print(my_list)

# Accept List elements and Find Count of given elements from List
# Find Odd numbers from list

















