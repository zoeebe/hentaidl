import telebot
import time
import requests
from bs4 import BeautifulSoup
import os
import zipfile

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Variable global para controlar el uso del comando /d
command_in_use = False

# Caracteres no válidos en los nombres de los archivos
invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

def sanitize_filename(filename):
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Hola! Usa el comando /d <id_manga> para descargar las imágenes.')

def download_images(id_manga, title, message):
    url = f"https://es.3hentai.net/d/{id_manga}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    images = soup.find_all('img', {'data-src': True})
    image_links = [img['data-src'].replace('t.jpg', '.jpg') for img in images]
    
    if not os.path.exists(title):
        os.makedirs(title)
    
    msg = bot.send_message(message.chat.id, "Descargando... 0/{}".format(len(image_links)))
    
    for i, link in enumerate(image_links):
        response = requests.get(link)
        with open(f"{title}/{i}.jpg", 'wb') as f:
            f.write(response.content)
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Descargando... {i+1}/{len(image_links)}")
    
    return image_links

def create_cbz(title):
    sanitized_title = sanitize_filename(title)
    with zipfile.ZipFile(f"{sanitized_title}.cbz", 'w') as zipf:
        for root, dirs, files in os.walk(title):
            for file in files:
                zipf.write(os.path.join(root, file))
    for file in os.scandir(title):
        os.remove(file.path)
    os.rmdir(title)

@bot.message_handler(commands=['d'])
def handle_command(message):
    global command_in_use
    if len(message.text.split()) == 1:
        # Responde al usuario que debe añadir un código para que el comando funcione
        bot.reply_to(message, "Debe añadir un codigo para que el comando funcione")
    else:
        if command_in_use:
            bot.send_message(message.chat.id, "Espere, se esta usando el comando")
            return
        command_in_use = True
        id_manga = message.text.split()[1]
        url = f"https://es.3hentai.net/d/{id_manga}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string
        title = sanitize_filename(page_title) + f" ({id_manga})"
    
        try:
            image_links = download_images(id_manga, title, message)
            create_cbz(title)
            with open(f"{title}.cbz", 'rb') as cbz_file:
                bot.send_document(message.chat.id, cbz_file)
            os.remove(f"{title}.cbz")
        except Exception as e:
            print(f"Error: {e}")
        command_in_use = False
        pass
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print('Error de conexion')
        # Espera 10 segundos antes de intentar reconectarse
        time.sleep(5)
