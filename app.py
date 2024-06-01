import sqlite3
from flask import Flask, request, render_template, redirect, url_for
import mysql.connector
import pymysql

app = Flask(__name__)

def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="PHW#84#jeor",
        database="washnwear"
    )

def fetch_total_revenue():
    # Connect to the database
    connection = pymysql.connect(host='localhost',
                                 user='root',
                                 password='PHW#84#jeor',
                                 database='washnwear')
    cursor = connection.cursor()

    # Query to calculate total revenue from the transactions table
    cursor.execute("SELECT SUM(TotalAmount) FROM transactions WHERE Status = 'completed'")
    total_revenue = cursor.fetchone()[0] or 0  # Fetch the total revenue value, defaulting to 0 if no transactions
    
    connection.close()
    
    return total_revenue

@app.route('/')
def index():
# Fetch total revenue
    total_revenue = fetch_total_revenue()
    
    # Render the template with the total revenue passed as a variable
    return render_template('index.html', total_revenue=total_revenue)
   

@app.route('/register_or_scan', methods=['POST'])
def register_or_scan():
    rfid = request.form['rfid']
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Customers WHERE RFID = %s", (rfid,))
    customer = cursor.fetchone()

    if not customer:
        return redirect(url_for('register_customer', rfid=rfid))
    
    cursor.close()
    conn.close()
    return redirect(url_for('select_services', customer_id=customer['CustomerID']))

@app.route('/register_customer/<rfid>', methods=['GET', 'POST'])
def register_customer(rfid):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Customers (RFID, Name, Email, Phone) VALUES (%s, %s, %s, %s)",
                       (rfid, name, email, phone))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    
    return render_template('register.html', rfid=rfid)

@app.route('/select_services/<customer_id>', methods=['GET', 'POST'])
def select_services(customer_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Services")
    services = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        selected_services = request.form.getlist('services')
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Transactions (CustomerID, TotalAmount, Status) VALUES (%s, %s, %s)",
                       (customer_id, 0, 'Pending'))
        transaction_id = cursor.lastrowid
        total_amount = 0

        for service_id in selected_services:
            cursor.execute("INSERT INTO TransactionDetails (TransactionID, ServiceID) VALUES (%s, %s)",
                           (transaction_id, service_id))
            cursor.execute("SELECT Price FROM Services WHERE ServiceID = %s", (service_id,))
            price = cursor.fetchone()[0]
            total_amount += price

        cursor.execute("UPDATE Transactions SET TotalAmount = %s WHERE TransactionID = %s",
                       (total_amount, transaction_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('payment', transaction_id=transaction_id))

    return render_template('select_services.html', services=services)

@app.route('/payment/<transaction_id>', methods=['GET', 'POST'])
def payment(transaction_id):
    if request.method == 'POST':
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Transactions SET Status = %s WHERE TransactionID = %s", ('Paid', transaction_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('status', transaction_id=transaction_id))
    
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT TotalAmount FROM Transactions WHERE TransactionID = %s", (transaction_id,))
    total_amount = cursor.fetchone()['TotalAmount']
    cursor.close()
    conn.close()

    return render_template('payment.html', total_amount=total_amount)

@app.route('/status/<transaction_id>')
def status(transaction_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.ServiceName, s.Price FROM TransactionDetails td
        JOIN Services s ON td.ServiceID = s.ServiceID
        WHERE td.TransactionID = %s
    """, (transaction_id,))
    services = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('status.html', services=services)

@app.route('/customers')
def customers():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Customers")
    customers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/customer/new', methods=['GET', 'POST'])
def create_customer():
    if request.method == 'POST':
        rfid = request.form['rfid']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Customers (RFID, Name, Email, Phone) VALUES (%s, %s, %s, %s)",
                       (rfid, name, email, phone))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('customers'))
    return render_template('customer_form.html', customer=None)

@app.route('/customer/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Customers WHERE CustomerID = %s", (customer_id,))
    customer = cursor.fetchone()
    if request.method == 'POST':
        rfid = request.form['rfid']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        cursor.execute("UPDATE Customers SET RFID = %s, Name = %s, Email = %s, Phone = %s WHERE CustomerID = %s",
                       (rfid, name, email, phone, customer_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('customers'))
    cursor.close()
    conn.close()
    return render_template('customer_form.html', customer=customer)

@app.route('/customer/delete/<int:customer_id>')
def delete_customer(customer_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Customers WHERE CustomerID = %s", (customer_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('customers'))

@app.route('/services')
def services():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT customers.Name AS CustomerName, 
       services.ServiceID, services.Servicename, services.ServiceDescription, services.Price, services.Addson
FROM services
INNER JOIN customers ON services.CustomerID = customers.CustomerID;


    """)
    services = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('services.html', services=services)


@app.route('/service/new', methods=['GET', 'POST'])
def create_service():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Services (ServiceName, ServiceDescription, Price) VALUES (%s, %s, %s)",
                       (name, description, price))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('services'))
    return render_template('service_form.html', service=None)

@app.route('/service/edit/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Services WHERE ServiceID = %s", (service_id,))
    service = cursor.fetchone()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        addson = request.form['addson']
        cursor.execute("UPDATE Services SET ServiceName = %s, ServiceDescription = %s, Price = %s Addson = %s WHERE ServiceID = %s",
                       (name, description, price, service_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('services'))
    cursor.close()
    conn.close()
    return render_template('service_form.html', service=service)

@app.route('/service/delete/<int:service_id>')
def delete_service(service_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Services WHERE ServiceID = %s", (service_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('services'))

@app.route('/transactions')
def transactions():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Transactions")
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('transactions.html', transactions=transactions)

@app.route('/transaction/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Transactions WHERE TransactionID = %s", (transaction_id,))
    transaction = cursor.fetchone()
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        total_amount = request.form['total_amount']
        status = request.form['status']
        cursor.execute("UPDATE Transactions SET CustomerID = %s, TotalAmount = %s, Status = %s WHERE TransactionID = %s",
                       (customer_id, total_amount, status, transaction_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('transactions'))
    cursor.close()
    conn.close()
    return render_template('transaction_form.html', transaction=transaction)

@app.route('/transaction/delete/<int:transaction_id>')
def delete_transaction(transaction_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Transactions WHERE TransactionID = %s", (transaction_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('transactions'))

@app.route('/audit')
def audit():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.TransactionID, t.CustomerID, t.Status, t.TotalAmount, s.ServiceName
        FROM Transactions t
        INNER JOIN Services s ON t.ServiceID = s.ServiceID
    """)
    audits = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('audit.html', audits=audits)



if __name__ == '__main__':
    app.run(debug=True)
