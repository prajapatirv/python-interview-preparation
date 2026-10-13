import math

def rev(num):
    return int(num != 0) and ((num % 10) * \
            (10**int(math.log(num, 10))) + \
                        rev(num // 10))

test_number = 123321
print ("The original number is : " + str(test_number))

res = test_number == rev(test_number)
print ("Is the number palindrome ? : " + str(res))

import math

def rev_sl(num):
    return int(num != 0) and ((num % 10) * \
            (10**int(math.log(num, 10))) + \
                        rev_sl(num // 10))

test_number = 9669669
print ("The original number is : " + str(test_number))

res = test_number == rev_sl(test_number)
print ("Is the number palindrome ? : " + str(res))


num = input("Enter a number")
if num == num[::-1]:
    print("Yes its a palindrome")
else:
    print("No, its not a palindrome")


def is_palindrome(num):
    original = num
    reverse = 0

    while num > 0:
        digit = num % 10
        reverse = reverse * 10 + digit
        num //= 10

    return original == reverse


print("121 is palindrom :  ", is_palindrome(121))    # True
print("123 is palindrom : ", is_palindrome(123))    # False