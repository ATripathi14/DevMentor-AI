# Attribute_error — calling a method that doesn't exist on an object (typo or wrong type assumption)


class BuyBook:
    def buy(self , name , price):
        self.name = name
        self.price = price
        print(f"Bought Book: {self.name} , Price: {self.price} ")

    def sell(self, name , price):
        self.name = name
        self.price = price
        print(f"Sold Book: {self.name} , Price: {self.price} ")


book = BuyBook()
book.buy("The Great Gatsby", 10.99)
book.sell("The Great Gatsby", 20.99)
book.loan("The Great Gatsby", 10.99) # AttributeError - no method of name 'loan'
