# Calculator program by Engr. Okpanya Dominic
import tkinter# Create the calculator interface

# Buttons on the calc. interface
button_values = [ 
    ["AC", "+/-", "%", "÷"],
    ["9", "8", "7", "×"],
    ["6", "5", "4", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "√", "="]
]

row_count = len(button_values)#5
column_count = len(button_values[0])

# variabls for the symbols
right_symbols = ["÷", "×", "-", "+", "="],
top_symbols = ["AC", "+/-", "-", "%"]

#define color to use
color_light_gray = "#D4D4D2"
color_black = "#1C1C1C"
color_dark_gray = "#505050"
color_orange = "#ff5900"
color_white = "white"


# The calculator's window settup
window = tkinter.Tk() # create the window
window.title("Calculator") # the window title
window.resizable(False, False) # For the window width and height


frame = tkinter.Frame(window) # Create the calc. frame inside the window
label = tkinter.Label(frame, text="0", font=("Arial", 50), background=color_black,
                      foreground=color_white ) # create the label inside frame


label.grid(row=0, column=0)
for row in range(row_count):
    for column in range(column_count):
        value = button_values[row][column]
        button = tkinter.Button(frame, text=value)
frame.pack()

window.mainloop() # Create the interface and keep the program running




