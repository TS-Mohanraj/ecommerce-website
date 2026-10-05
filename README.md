# Sun Auto Centre

Sun Auto Centre is a Flask and SQLite motorcycle parts and accessories shop. The existing Bootstrap storefront and product images are served by Flask; customer accounts, carts, inventory, orders, and returns are stored in SQLite.

The old Express/Node backend and its owner/product seed scripts have been retired; use the Flask application and its database setup commands below.

## Requirements

- Python 3.10 or newer
- pip

## Install on Windows

From the project folder in PowerShell:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the interpreter directly:

```powershell
.\env\Scripts\python.exe -m pip install -r requirements.txt
```

## Create an administrator and run Flask

Create the first administrator interactively. The password is prompted securely and stored only as a password hash:

```powershell
.\env\Scripts\python.exe -m flask --app app create-admin
```

Reset an existing administrator password the same way. Use a password manager to generate and retain a unique password; the CLI prompts twice without echoing it:

```powershell
.\env\Scripts\python.exe -m flask --app app reset-admin --username <administrator>
```

Then start the application:

```powershell
.\env\Scripts\python.exe app.py
```

Open <http://127.0.0.1:5000/>. The administrator login is at <http://127.0.0.1:5000/admin/login>.

For a deployed HTTPS site, configure a strong `SECRET_KEY` environment variable and set `COOKIE_SECURE=true`. Local development automatically creates a persistent secret under the ignored `instance/` directory.

## Database and inventory

The application creates and migrates `database/products.db` when it starts. It retains the existing 22 products and historical customer/order data, seeds only missing catalog items, and upgrades legacy customer passwords to hashes. Products are not physically deleted; deactivation preserves order history.

The live SQLite database can contain customer contact information, addresses, orders, and password hashes. It and its SQLite sidecar files are ignored by Git; do not force-add or commit them. Back up business data securely outside the repository.

The one-time random administrator passwords generated while securing the existing local database are stored in a user-restricted file under `%LOCALAPPDATA%\SunAutoCentre\credentials`. Retrieve those locally only, then move them into a password manager. If that file is unavailable, set new credentials with `reset-admin`; passwords are never displayed by the command.

The original catalog had no stock values, so the first verified setup assigned a clearly marked **test stock of 5 units per existing product**. This is test data, not a claim about physical inventory; confirm and replace quantities in **Products & Stock** before accepting real orders. The two existing “Contact for Price” products remain non-purchasable until an administrator enters a valid price.

## Customer checks

1. Open **Sign Up**, register with a valid 10-digit mobile number and password of at least 8 characters, then log in.
2. Update the name, mobile number, and delivery address under **My Account**.
3. Browse **Products**, open a product detail page, and add an in-stock priced product to the cart.
4. Change quantities or remove products in the cart, then place an order.
5. Find the order and its saved item/price snapshots under **My Orders**.
6. An administrator must mark the order **Delivered** before a return can be requested. Request the return within 7 days of the recorded delivery timestamp and follow its status under **My Returns**.

## Run tests

```powershell
.\env\Scripts\python.exe -m unittest discover -s tests -v
```

The automated tests use temporary SQLite databases and do not change the working catalog database.
