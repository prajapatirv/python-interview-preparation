# Immutable
"""
    Multiline String:--Notes
    id(var_name):-Address of given variable
"""
a=30
b=20
c=30
print("A:",a," Type:",type(a)," Address:",id(a))
print("B:",b," Type:",type(b)," Address:",id(b))
print("C:",c," Type:",type(c)," Address:",id(c))

# c=a+b # 50
c=20
print("After Modification :")
print("A:",a," Type:",type(a)," Address:",id(a))
print("B:",b," Type:",type(b)," Address:",id(b))
print("C:",c," Type:",type(c)," Address:",id(c))

