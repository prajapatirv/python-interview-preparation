"""
Create Class of Books
bookName
authorName
price

parameterized constructor
display method to print details

Apply for loop to accept 5 book details and add into List
Then even display list elements
"""
class Books:
    def __init__(self,bookName,authorName,price):
        self.bookName=bookName
        self.authorName=authorName
        self.price=price

    def display(self):
        print("Book Name:",self.bookName,"\nAuthor Name:",self.authorName,
              "\nPrice:",self.price)
        # List
books=[]
count=int(input("Enter Book Count:"))#2
for val in range(count):#0 and 1
    bn=input("Enter Book Name:")
    an=input("Enter Author Name:")
    p=int(input("Enter Price:"))

    # Wrap details into Object of class
    book=Books(bn,an,p)
    # Add Object into list
    books.append(book)

print("Book Details:")
for book in books:
    book.display()
    print("----------------------------")

