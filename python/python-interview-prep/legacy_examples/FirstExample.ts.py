"""
name="Sonali"

permanent Storage
File System
open("File_Name","mode")
r,w,a-modes
text file--t
binary file--b

w mode
It will create file if file is not exist

Database
"""
# f=open("Files/employee_info.txt","at")

# ******************* Write File ****************************
# name=input("Enter Employee Name:")
# age=int(input("Enter Age:"))
# salary=float(input("Enter Salary:"))
#
# info=name+"\t"+str(age)+"\t"+str(salary)+"\n"
# print(info)
# f.write(info)

# list=["Komal Jadhav\t23\t50000\n","Omkar Mindhe\t27\t170000\n","Prasad Korder\t28\t60000\n"]
# f.writelines(list)


# ************************** Read Mode *************************
"""
read():-- all data from file
read(count_of_char):- read given number of char only
readLine() :-- read single in each call
readLines():- it will read all lines in list format
"""
f=open("Files/employee_info.txt","rt")
# data=f.read()
# data=f.read(4)
# print(data)

# line1=f.readline()
# line2=f.readline()
# line3=f.readline()
# print(line1+"\n"+line2+"\n"+line3)

lines=f.readlines()
print(lines)
for line in lines:
    print(line)

# find count of Lines /words and char from file
# Find count of vowels