# """
# if-else:- conditional statement
# if condition:
#     statements--if condition returns true
# else:
#     statements--if condition returns false
#
# Relational Operators:-</>/<=/>=/==/!=
#
# Max number from given 2 numbers
# """
# a=int(input("Enter First Number:"))# 23
# b=int(input("Enter Second Number:"))#50
# # 23>50----False
# if a>b:
#     print(a," is a greater number.")
# else:
#     print(b," is a greater number")
#
#
# """
# check for even and odd :-
#
# % :- Arithmetic Operator (Modulus -reminder after division)
# """
# no=int(input("Enter Number:"))
# if no % 2==0:
#     print(no," is a even number.")
# else:
#     print(no," is a odd number.")
#
#
# """
# Max number from given 3 numbers
# a=3,b=7,c=100
#
# 1--a is bigger number
# a>b and a>c
# 2--b is a bigger number
# b>c
# 3--c is bigger number
#
# if-elif-else
# """
# a=int(input("Enter First Number:"))# 23
# b=int(input("Enter Second Number:"))#50
# c=int(input("Enter Third Number:"))
# if a>b and a>c:
#     print(a,"is is a max number.")
# elif b>c:
#     print(b,"is a max number.")
# else:
#     print(c,"is a max number.")
"""
Accept number from user check whether given number
is a natural number or not
if it is natural number then find average of n natural numbers
and display it
if not then print appropriate massage

7-----1,2,3,4,5,6,7/7 return
Loops:-- for /while
range(endList):--0-----endLimit-1
range(starLimit,endLimit)
"""
# no=int(input("Enter Number"))# 5--1,5--6--terminate my loop
# # print(range(no))
# if(no>0):
#     sum=0
#     for val in range(1,no+1):
#         sum=sum+val
#     print("Average is:",(sum/no))
# else:
#     print("Please Enter Valid Natural Number.")

# range(10,0,-1)

# for x in range(10,0,-3):
#     print(x)


"""
Print Table of given number
no=3
3*1=3
3*2=6

3*10=30
"""
no=int(input("Enter Number"))
index=1
while index<=10:
    print(no*index)
    index=index+1
print("Index Outside:",index)#11












































