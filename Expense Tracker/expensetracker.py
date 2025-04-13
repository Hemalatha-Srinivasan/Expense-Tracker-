import mysql.connector 
import tkinter as tk
from tkinter import BOTTOM, HORIZONTAL, RIGHT, VERTICAL, X, Y, Scrollbar, messagebox
from tkinter import ttk, messagebox
from datetime import datetime
import speech_recognition as sr
from fpdf import FPDF
import fitz 
import requests
import google.generativeai as genai

GENAI_API_KEY = "AIzaSyAESKkvyzxKwx6nAy8CohOL9cnuzsF5N1w"  # Replace with your Gemini API key
genai.configure(api_key=GENAI_API_KEY)

# Step 1: Database Connection with Error Handling

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",  # Change this to your MySQL username
        password="*******",  # Change this to your MySQL password
        database="expense_tracker"
    )
    cursor = db.cursor()
except mysql.connector.Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit()

# Step 3: GUI - Expense Entry (Tkinter)
def load_expenses():

    # Clear all existing rows in UI
    table.delete(*table.get_children())  

    # Fetch updated expense data from database
    cursor.execute("SELECT id, category, amount, date, notes FROM expenses ORDER BY date DESC")
    expenses = cursor.fetchall()

    # Insert new data into table with proper numbering
    for i, expense in enumerate(expenses, start=1):
        table.insert("", "end", values=(expense[0], expense[1], expense[2], expense[3], expense[4]))  # Include ID

    print("✅ Expenses successfully loaded!")

# Step 2: Function to Add Expense to MySQL

def add_expense(category, amount, date, notes):
    try:
        sql = "INSERT INTO expenses (category, amount, date, notes) VALUES (%s, %s, %s, %s)"
        values = (category, amount, date, notes)
        cursor.execute(sql, values)
        db.commit()
        print("✅ Expense added successfully.")
    except mysql.connector.Error as e:
        print(f"❌ MySQL Error: {e}")
        load_expenses()

def submit_expense():
    category = category_entry.get().strip()
    amount_str = amount_entry.get().strip()
    date_str = date_entry.get().strip()  # Expected in DD.MM.YYYY format
    notes = notes_entry.get().strip()
    
    if not category or not amount_str or not date_str:
        messagebox.showerror("❌ Error", "Please fill all fields!")
        return
    
    try:
        amount = float(amount_str)
    except ValueError:
        messagebox.showerror("❌ Error", "Amount must be a number!")
        return
    
    try:
        # Convert manually entered date from DD.MM.YYYY to YYYY-MM-DD for MySQL
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        date_formatted = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        messagebox.showerror("❌ Error", "Date must be in DD.MM.YYYY format!")
        return
    
    add_expense(category, amount, date_formatted, notes)
    messagebox.showinfo("✅ Success", "Expense recorded successfully!")
    
    # Clear the form fields after submission
    category_entry.delete(0, tk.END)
    amount_entry.delete(0, tk.END)
    date_entry.delete(0, tk.END)
    notes_entry.delete(0, tk.END)
    load_expenses()

# Step 4: Voice Input for Expenses (Updated to Require Full Date)

def voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Speak your expense (e.g., 'Groceries 1200 on 15th August 2004 for Cooking')")
        try:
            audio = recognizer.listen(source)
            text = recognizer.recognize_google(audio)
            print(f"🎙 Recognized: {text}")

            words = text.split()
            if len(words) < 2:
                print("❌ Insufficient information from voice input.")
                return

            # Extract category and amount
            category = words[0]
            amount = float(words[1])

            # Require that "on" is present to specify a date
            if "on" not in words:
                print("❌ Voice note must include a date after 'on' (e.g., 'on 15th August 2004').")
                return

            idx = words.index("on")
            if len(words) <= idx + 3:
                print("❌ Incomplete date information in voice note. Please provide day, month, and year.")
                return

            # Extract and format date
            day_word = words[idx + 1]
            month_word = words[idx + 2]
            year_word = words[idx + 3]

            if day_word[-2:].lower() in ['st', 'nd', 'rd', 'th']:
                day_clean = day_word[:-2]
            else:
                day_clean = day_word

            try:
                date_obj = datetime.strptime(f"{day_clean} {month_word} {year_word}", "%d %B %Y")
                date_formatted = date_obj.strftime("%Y-%m-%d")
            except Exception as e:
                print(f"❌ Could not parse date from voice input: {e}")
                return

            # Extract notes (if any)
            note = " ".join(words[idx + 4:]) if len(words) > idx + 4 else ""

            # Insert into the database with a unique ID
            cursor.execute(
                "INSERT INTO expenses (category, amount, date, notes) VALUES (%s, %s, %s, %s)",
                (category, amount, date_formatted, note),
            )
            db.commit()

            print("✅ Voice expense added successfully.")
            load_expenses()  # Refresh table

        except sr.UnknownValueError:
            print("❌ Could not understand audio")
        except sr.RequestError:
            print("❌ Could not request results")
        except Exception as e:
            print(f"❌ Error processing voice input: {e}")

#edit expense 
def edit_expense():
    '''This function allows the user to edit the details of a selected expense.'''

    # Check if an expense is selected
    selected_item = table.selection()
    if not selected_item:
        messagebox.showerror("Error", "No expense selected! Please select an expense from the table.")
        return

    # Get selected row details
    item = table.item(selected_item)
    expense_id = item['values'][0]  # Get ID from the selected row
    category, amount, date, notes = item['values'][1:]

    # Populate form fields with the selected expense data
    category_entry.delete(0, tk.END)
    category_entry.insert(0, category)
    amount_entry.delete(0, tk.END)
    amount_entry.insert(0, amount)
    date_entry.delete(0, tk.END)
    date_entry.insert(0, datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y"))
    notes_entry.delete(0, tk.END)
    notes_entry.insert(0, notes)

    def clear_fields():
        '''Clears all input fields after updating an expense.'''
        category_entry.delete(0, tk.END)
        amount_entry.delete(0, tk.END)
        date_entry.delete(0, tk.END)
        notes_entry.delete(0, tk.END)

    def update_expense():
        '''Updates the selected expense in the database and UI table.'''
        new_category = category_entry.get().strip()
        new_amount_str = amount_entry.get().strip()
        new_date_str = date_entry.get().strip()
        new_notes = notes_entry.get().strip()

        try:
            new_amount = float(new_amount_str)  # Validate amount
            new_date = datetime.strptime(new_date_str, "%d.%m.%Y").strftime("%Y-%m-%d")  # Validate date format
        except ValueError:
            messagebox.showerror("Error", "Invalid amount or date format!")
            return
        
        try:
            # Execute MySQL UPDATE query
            cursor.execute(
                "UPDATE expenses SET category=%s, amount=%s, date=%s, notes=%s WHERE id=%s",
                (new_category, new_amount, new_date, new_notes, expense_id),
            )
            db.commit()

            # *CLEAR & RELOAD UI TO PREVENT DUPLICATES*
            table.delete(*table.get_children())  # Clears all rows from UI
            load_expenses()  # Reload from database

            # Clear fields after update ✅
            clear_fields()

            # Reset form & button
            messagebox.showinfo("Success", "Expense updated successfully!")
            submit_btn.config(command=submit_expense, text="Submit Expense")  

        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", f"❌ Error updating expense: {e}")

    # Change submit button action to update the expense
    submit_btn.config(command=update_expense, text="Update Expense")

# Delete Expense
def delete_expense():
    '''Deletes a selected expense from the database and UI.'''

    selected_item = table.selection()
    if not selected_item:
        messagebox.showerror("Error", "Please select an expense to delete!")
        return

    item = table.item(selected_item)
    expense_id = item['values'][0]  # Get the ID of the selected expense

    confirmation = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this expense?")
    if confirmation:
        try:
            # Execute DELETE query
            cursor.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
            db.commit()

            # 🛠 *CLEAR UI TABLE & RELOAD UPDATED DATA*
            table.delete(*table.get_children())  # Clear all rows from UI
            load_expenses()  # Reload updated data

            messagebox.showinfo("Success", "Expense deleted successfully!")

        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", f"❌ Error deleting expense: {e}")

# Step 5: PDF Generation

def generate_pdf():
    # Retrieve expenses for the current month and year
    cursor.execute("SELECT * FROM expenses WHERE MONTH(date) = MONTH(CURDATE()) AND YEAR(date) = YEAR(CURDATE())")
    expenses = cursor.fetchall()

    if not expenses:
        print("⚠ No expenses found for this month.")
        return

    pdf = FPDF()
    pdf.add_page()

    # Set up title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Monthly Expense Report", 0, 1, 'C')
    pdf.ln(5)

    # Define column headers and widths
    headers = ["ID", "Category", "Amount", "Date", "Notes"]
    col_widths = [20, 40, 30, 30, 70]  # Adjust widths as needed

    # Header row
    pdf.set_font("Arial", 'B', 12)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 10, header, 1, 0, 'C')
    pdf.ln()

    # Data rows with sequential numbering starting from 1
    pdf.set_font("Arial", '', 12)
    total_amount = 0  # Initialize total amount
    row_number = 1
    for expense in expenses:
        pdf.cell(col_widths[0], 10, str(row_number), 1, 0, 'C')
        pdf.cell(col_widths[1], 10, expense[1], 1, 0, 'C')
        pdf.cell(col_widths[2], 10, f"{expense[2]:.2f}", 1, 0, 'C')  # Amount
        total_amount += expense[2]  # Add amount to total
        
        try:
            date_display = datetime.strptime(str(expense[3]), "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            date_display = str(expense[3])
        pdf.cell(col_widths[3], 10, date_display, 1, 0, 'C')
        pdf.cell(col_widths[4], 10, expense[4], 1, 0, 'C')
        pdf.ln()
        row_number += 1

    # Add total amount at the bottom
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(sum(col_widths[:-1]), 10, "Total Expenses:", 1, 0, 'R')  # Span across all columns except last
    pdf.cell(col_widths[-1], 10, f"{total_amount:.2f}", 1, 1, 'C')  # Display total amount

    pdf.output("Monthly_Report.pdf")
    print("✅ PDF Report Generated.")

# Step 6: AI Analysis using Gemini AI (Improved)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    return text

# Function to analyze expenses
def analyze_expenses(pdf_path):
    try:
        pdf_text = extract_text_from_pdf(pdf_path)
        
        if not pdf_text.strip():
            return "❌ Error: No readable text found in the PDF. It might be scanned or encrypted."

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Analyze this expense report and provide insights:\n\n{pdf_text}")

        return response.text

    except Exception as e:
        return f"❌ Error analyzing expenses: {e}"

# Replace with your actual file

def show_insights():
    pdf_path = "Monthly_Report.pdf" 
    insights = analyze_expenses(pdf_path)
    insights_window = tk.Toplevel(root)
    insights_window.title("💡 Expense Insights")
    insights_label = tk.Label(insights_window, text=insights, wraplength=500, justify="left")
    insights_label.pack(pady=10)

# Step 7: Tkinter GUI Setup

# date_entry.grid(row=2, column=1)

root = tk.Tk()
root.title("Expense Tracker")
root.geometry("900x500")
root.configure(bg="white")

# Left Frame: Expense Entry Form
left_frame = tk.Frame(root, padx=10, pady=10, bg = "#42224a")
left_frame.pack(side="left", fill="y", padx=10, pady=10)

tk.Label(left_frame, text="EXPENSE TRACKER", font=("Arial", 12, "bold"), bg="#42224a",fg="white").grid(row=0, column=0, columnspan=2, pady=5)

tk.Label(left_frame, text="ADD EXPENSE", font=("Arial", 12, "bold"), bg="#42224a",fg="white").grid(row=1, column=0, columnspan=2, pady=10)

# Category
tk.Label(left_frame, text="Category:", bg="#42224a", fg="white").grid(row=2, column=0, sticky="w")
category_entry = ttk.Entry(left_frame)
category_entry.grid(row=2, column=1, padx=5, pady=5)

# Amount
tk.Label(left_frame, text="Amount:", bg="#42224a", fg="white").grid(row=3, column=0, sticky="w")
amount_entry = ttk.Entry(left_frame)
amount_entry.grid(row=3, column=1, padx=5, pady=5)

# Date
tk.Label(left_frame, text="Date (DD.MM.YYYY):", bg="#42224a", fg="white").grid(row=4, column=0, sticky="w")
date_entry = ttk.Entry(left_frame)
date_entry.grid(row=4, column=1, padx=5, pady=5)

#Notes
tk.Label(left_frame, text="Notes:", bg="#42224a",fg="white").grid(row=5, column=0, sticky="w")
notes_entry = ttk.Entry(left_frame)
notes_entry.grid(row=5, column=1, padx=5, pady=5)


# Buttons (Add Expense & Reset)
btn_frame = tk.Frame(left_frame,bg="#42224a")
btn_frame.grid(row=6, column=0, columnspan=2, pady=20)

submit_btn = tk.Button(btn_frame, text="Submit Expense", bg="#E5D9F2", fg="#42224a", width=12, command=submit_expense)
submit_btn.pack(side="left", padx=5)

voice_btn = tk.Button(btn_frame, text="voice input", bg="#E5D9F2", fg="#42224a", width=12, command=voice_input)
voice_btn.pack(side="left", padx=5)

# Right Frame: Expense Table
right_frame = tk.Frame(root, padx=10, pady=10,bg = "#E5D9F2")
right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

# Buttons (Export & AI Insights)
top_btn_frame = tk.Frame(right_frame,bg="#E5D9F2")
top_btn_frame.pack(fill="x", pady=5)

export_btn = tk.Button(top_btn_frame, text="Generate PDF", bg="#42224a", fg="white" , command=generate_pdf, width=30)
export_btn.pack(side="left", padx=5)

ai_insights_btn = tk.Button(top_btn_frame, text="AI Insights", bg="#42224a", fg="white", command=show_insights, width=30)
ai_insights_btn.pack(side="left", padx=5)

# Buttons (View, Edit, Delete)
action_btn_frame = tk.Frame(right_frame,bg="#E5D9F2")
action_btn_frame.pack(fill="x", pady=5)


edit_btn = tk.Button(action_btn_frame, text="Edit", bg="#42224a", fg="white", command=edit_expense, width=30)
edit_btn.pack(side="left", padx=5)

delete_btn = tk.Button(action_btn_frame, text="Delete", bg="#42224a", fg="white", command=delete_expense, width=30)
delete_btn.pack(side="left", padx=5)

style=ttk.Style()
style.configure("Treeview", 
                background="white",  
                rowheight=30,          # Row Height
                fieldbackground="white")
style.configure("Treeview.Heading", 
                background="#42224a",  
                foreground="#42224a",     
                font=("Arial", 10, "bold")) 
style.map("Treeview", background=[("selected", "#42224a")],  # Highlight selection in purple
          foreground=[("selected", "#E5D9F2")]) 

# Expense Table
columns = ("S. No", "Category", "Amount", "Date", "Notes")
table = ttk.Treeview(right_frame, columns=columns, show="headings", height=8, style="Treeview")
table.pack(fill="both", expand=True)

Xaxis_Scrollbar = Scrollbar(  
        table,  
        orient = HORIZONTAL,  
        command = table.xview  
        )  
Yaxis_Scrollbar = Scrollbar(  
        table,  
        orient = VERTICAL,  
        command = table.yview  
        )  
Xaxis_Scrollbar.pack(side = BOTTOM, fill = X)  
Yaxis_Scrollbar.pack(side = RIGHT, fill = Y)  

table.config(yscrollcommand = Yaxis_Scrollbar.set, xscrollcommand = Xaxis_Scrollbar.set)  
 
for col in columns:
    table.heading(col, text=col)
    table.column(col, width=100)

load_expenses()

root.mainloop()