from typing import Final
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CallbackContext, ConversationHandler
import requests
import pandas as pd
from bs4 import BeautifulSoup
import Constans as constant
import re
import numpy as np
import ast
from datetime import datetime
import matplotlib.pyplot as plt
import json
from io import BytesIO

NOMBRE, URL, TARGET = range(3)
headers = {"User-Agent": constant.HEADERS} #My user agent
url_db = "urldb.csv"

try:
    # Intenta leer el archivo CSV
    df = pd.read_csv(url_db)
except pd.errors.EmptyDataError:
    # Si el archivo está vacío, crea un DataFrame vacío
    df = pd.DataFrame({"NameId", "Name", "Price","PriceTarget","Alarm", "URL", "PriceHistory", "DateHistory", "Sale", "SaleBoolean"})

############################### Chek prices ############################################
async def check_prices (context: ContextTypes.DEFAULT_TYPE):
   url_array = df["URL"].to_numpy()
   alert_array = df["Alarm"].to_numpy()
   names_array = df["NameId"].to_numpy()
   target_array = df["PriceTarget"].to_numpy()
   sale_array = df["Sale"].to_numpy()
   sale_bool_array = df["SaleBoolean"].to_numpy()
   print("Comienza track")

   for i in range(len(url_array)):
        page = requests.get(url_array[i], headers=headers)
        soup = BeautifulSoup(page.content, 'html.parser')

        
        price = soup.find(attrs="a-offscreen").get_text()
        sale = soup.find(attrs= "a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin savingsPercentage")#.get_text()
    
        if sale == None:
          sale = "0%"
          salebool = False
        else:
          sale = sale.get_text()
          salebool = True


        df.at[i, "Price"] = price
        df.at[i, "Sale"] = sale
        df.at[i, "SaleBoolean"] = salebool

        price_history = df.at[i, "PriceHistory"]
        numeric_price = float(price.replace("€", "").replace(",", "."))
        original_list = ast.literal_eval(price_history)
        float_list = [float(element) for element in original_list]
        
        if len(float_list) == 5:
            float_list.pop(0)  # Eliminar el elemento más antiguo
        float_list.append(numeric_price)
        
        string_list = [str(element) for element in float_list]
        df.at[i, "PriceHistory"] = string_list

        date_history = df.at[i, "DateHistory"]
        original_datetime_list = eval(date_history)
        
        fecha_hora_actual = datetime.now()
        formato_personalizado = "%Y-%m-%d %H:%M"
        fecha_hora_formateada = fecha_hora_actual.strftime(formato_personalizado)
       
        if len(original_datetime_list) == 5:
           original_datetime_list.pop(0)
        original_datetime_list.append(fecha_hora_formateada)
        df.at[i, "DateHistory"] =original_datetime_list

        df.to_csv(url_db, index=False)

        if alert_array[i] == True:
            if numeric_price <= float(target_array[i]):
                await context.bot.send_message(chat_id=constant.CHAT_ID, text=f"El producto: {names_array[i]} esta por debajo de su precio target a {price}€ ")
            if sale_bool_array[i] == True:
                await context.bot.send_message(chat_id=constant.CHAT_ID, text=f"El producto {names_array[i]} esta rebajado un  {sale_array[i]}: {price} ")
        df.to_csv(url_db, index=False)  
        

   print("Precio trackeado")

############################### Start function ############################################
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = "Bienvenido al Amazon Price Tracker realizado para la práctica 2 de la asignatura de Robotica"+"\r\n\n"+"Si necesitas ayuda para el uso del bot /help"
    await update.message.reply_text(welcome_message)

############################### Help function ############################################
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message ="Los comandos necesarios para el uso de este bot:" + "\r\n\n" + "🔗/track para introducir un producto" + "\r\n" + "📋/list para mostrar productos trackeados y las siguientes funciones:" + "\r\n" + "       - 💵 Precio del producto" + "\r\n" + "       - 🗑️ Borrar producto" + "\r\n" + "       - 🔙 Volver atras"
    message = await update.message.reply_text(help_message)
    await context.bot.pin_chat_message(chat_id=update.message.chat_id, message_id=message.message_id)

############################### Track function ############################################
# Función para iniciar la conversación
async def track(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Hola! Para almacenar un producto, por favor, proporciona el nombre del producto.")
    
    return NOMBRE

# Función para manejar el nombre del producto
async def handle_nombre(update: Update, context: CallbackContext) -> int:
    context.user_data['nombre'] = update.message.text
    await update.message.reply_text(f"Nombre del producto: {context.user_data['nombre']}\nAhora, por favor, proporciona la URL del producto en.")
    return URL

# Función para manejar la URL del producto
async def handle_url(update: Update, context: CallbackContext) -> int:
    user_url = update.message.text

    # Verificar si la URL comienza con "https://www.amazon." y contiene "/dp/"
    if not user_url.startswith("https://www.amazon.") or "/dp/" not in user_url:
        await update.message.reply_text("No es una URL de producto de Amazon válida. Por favor, proporciona una URL válida.")
        return URL  # Permite que el usuario proporcione la URL nuevamente
    
    # La URL es válida, dividir la URL para obtener la parte específica
    product_path = user_url.split("/dp/")[-1].split("/")[0]

    # Construir la URL completa con el dominio y "/dp/"
    amazon_domain = user_url.split("/dp/")[0]
    context.user_data['url'] = f"{amazon_domain}/dp/{product_path}"

    page = requests.get(user_url , headers = headers)

    soup = BeautifulSoup(page.content, 'html.parser')

    title = soup.find(id = "productTitle").get_text()
    price = soup.find(attrs = "a-offscreen").get_text()
    sale = soup.find(attrs= "a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin savingsPercentage")#.get_text()
    

    if sale == None:
      sale = "0%"
      salebool = False
    else:
       sale = sale.get_text()
       salebool = True

    print(sale)
    
    numeric_price = price.replace("€", "").replace(",", ".")
    
    fecha_hora_actual = datetime.now()
    formato_personalizado = "%Y-%m-%d %H:%M"
    fecha_hora_formateada = fecha_hora_actual.strftime(formato_personalizado)

    l = len(df["URL"])
    df.loc[l, ["Name"]] = title.strip() 
    df.loc[l, ["URL"]] = context.user_data['url']
    df.loc[l, ["Price"]] = price.strip()
    df.loc[l, ["PriceTarget"]] = 0
    df.loc[l, ["NameId"]] = context.user_data['nombre']
    df.loc[l, ["Alarm"]] = False
    df.loc[l, ["PriceHistory"]] = str([numeric_price,numeric_price])
    df.loc[l, ["DateHistory"]] = str([fecha_hora_formateada,fecha_hora_formateada])
    df.loc[l, ["Sale"]] = sale
    df.loc[l, ["SaleBoolean"]] = salebool
    
    df.drop_duplicates(subset=["URL", "Name"], keep="first", inplace=True)  
    df.to_csv(url_db, index= False)

    await update.message.reply_text("Producto almacenado.\n\nNombre: {}\nURL: {}".format(
        context.user_data['nombre'],
        context.user_data['url']
    ))
    return ConversationHandler.END    

# Función para manejar la cancelación de la conversación
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

############################### List buttons ############################################
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  num_rows = len(df)
  keyboard =[] 
  names_array = df["NameId"].to_numpy()
 
  for i in range(num_rows):
        call = 'm0' + str(i) 
        boton = InlineKeyboardButton(names_array[i], callback_data=call)
        keyboard.append([boton])
  
  boton = InlineKeyboardButton('❌ Cancelar', callback_data='cancel_menu')
  keyboard.append([boton])
  reply_markup = InlineKeyboardMarkup(keyboard)
    
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text('Choose the option in main menu:', reply_markup=reply_markup)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  num_rows = len(df)
  keyboard =[] 
  names_array = df["NameId"].to_numpy()

  for i in range(num_rows):
        call = 'm0' + str(i) 
        boton = InlineKeyboardButton(names_array[i], callback_data=call)
        keyboard.append([boton])
  
  boton = InlineKeyboardButton('❌ Cancelar', callback_data='cancel_menu')
  keyboard.append([boton])
  reply_markup = InlineKeyboardMarkup(keyboard)

  query = update.callback_query
  await query.answer()
  await query.edit_message_text(text='Choose the option in main menu:', reply_markup=reply_markup)

async def cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  await query.edit_message_text(text= 'Has salido de la lista de productos')

async def sub_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query

  match = re.match(r'm0(\d+)', query.data)
  
  names_array = df["NameId"].to_numpy()
  text = names_array[int(match.group(1))]
  
  await query.answer()
  await query.edit_message_text(
                        text= text,
                        reply_markup= await first_menu_keyboard(match.group(1)))

async def alarm_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  alert_array = df["Alarm"].to_numpy()
  match = re.match(r'alarm(\d+)', query.data)
  
  if alert_array[int(match.group(1))] == False:
    df.at[int(match.group(1)), "Alarm"] = True
    text = 'Alerta activada'
  else:
    df.at[int(match.group(1)), "Alarm"] = False
    text = 'Alerta desactivada'
    
  df.to_csv(url_db, index=False)
  
  await query.answer()
  await query.edit_message_text(text = text)
  
async def price_print(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  
  match = re.match(r'price(\d+)', query.data)
  
  price_array = df["Price"].to_numpy()
  names_array = df["NameId"].to_numpy()
  target_array = df["PriceTarget"].to_numpy()

  target_numeric = re.search(r'\d+', str(target_array[int(match.group(1))])).group() 
  
  if int(target_numeric) > 0: 
    text = 'Precio de ' + names_array[int(match.group(1))] + ": " + str(price_array[int(match.group(1))]) + "\r\n" + "Precio target: " + str(target_array[int(match.group(1))]) + "€."
  else:
    text = 'Precio de ' + names_array[int(match.group(1))] + ": " + str(price_array[int(match.group(1))]) + ".\r\n" + "No hay precio target." 
  
  await query.answer()
  await query.edit_message_text(text= text)

async def target_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    match = re.match(r'target(\d+)', query.data)
    selected_index = int(match.group(1))
    price_array = df.at[selected_index, "Price"]
 
    target_array = df.at[selected_index, "PriceTarget"]
    target_numeric = re.search(r'\d+', str(target_array)).group()  # Corrección aquí
    
    if int(target_numeric) > 0: 
        text = 'El producto vale: ' + str(price_array) + '.\r\n' + 'Tiene un price target de: ' + str(target_array) + '.\r\n' + 'Indica qué precio deseas establecer como objetivo, suministra 0 si quieres eliminar este precio:'
    else:
        text = 'El producto vale: ' + str(price_array) + '.\r\n' + 'No tiene price target.'  + '\r\n' + 'Indica qué precio deseas establecer como objetivo:'

    await query.answer()
    await query.edit_message_text(text=text)

    context.user_data['selected_product_index'] = selected_index
    context.user_data['in_target_product'] = True


async def set_price_target(update: Update, context: CallbackContext):
    user_reply = update.message.text

    if context.user_data.get('in_target_product', False):
        # Remove the Euro symbol and any leading/trailing whitespaces
        user_reply_numeric = user_reply.replace('€', '').strip()

        # Convert to float
        price_target_numeric = float(user_reply_numeric)

        context.user_data["price_target"] = f"{price_target_numeric} €"
        selected_index = context.user_data.get('selected_product_index')

        numeric_price_target = pd.to_numeric(context.user_data["price_target"].replace("€", "").strip(), errors='coerce')

        # Set the PriceTarget column with the numeric value
        df.at[selected_index, "PriceTarget"] = numeric_price_target
        df.to_csv(url_db, index=False)  # Save the changes to the CSV file

        if int(user_reply) > 0:
            text = "¡Precio objetivo establecido como " + user_reply + " €!"
        else:
            text = "Precio objetivo eliminado"
        await update.message.reply_text(text)

async def history_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    query = update.callback_query
    match = re.match(r'historial(\d+)', query.data)
    
    price_history = df.at[int(match.group(1)), "PriceHistory"]
    date_history = df.at[int(match.group(1)), "DateHistory"]

    # Convertir las listas a cadenas JSON
    price_history_json = json.dumps(price_history)
    date_history_json = json.dumps(date_history)

    # Convertir las cadenas JSON a listas
    date_list = json.loads(date_history_json)
    price_list = [float(price) for price in json.loads(price_history_json)]

    # Convertir las cadenas de fecha en objetos datetime
    date_list = [datetime.strptime(date_str, "%Y-%m-%d %H:%M") for date_str in date_list]

    # Graficar los puntos
    plt.rcParams["figure.figsize"] = [7.50, 3.50]
    plt.rcParams["figure.autolayout"] = True
    print(len(date_list))
    print(len(price_list))
    plt.plot(date_list, price_list, marker='o')
    plt.xlabel('Fecha')
    plt.ylabel('Precio (€)')
    plt.title('Gráfico de Precio a lo largo del Tiempo')

    # Guardar la figura en un BytesIO
    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    # Enviar la imagen al chat
    await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_stream)

    # Limpiar la figura para la próxima vez
    plt.clf()

    await query.answer()
    await query.edit_message_text(text='Grafica')

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    match = re.match(r'delete(\d+)', query.data)

    df.drop(int(match.group(1)), inplace=True)
    df.to_csv(url_db, index=False)
    
    await query.answer()
    await query.edit_message_text(text= 'Articulo borrado')

async def first_menu_keyboard(i):
  alert_array = df["Alarm"].to_numpy()
  url_array = df["URL"].to_numpy()
  call_compra = 'compra' + i 
  call_target = 'target' + i
  call_alarm = 'alarm' + i
  call_precio = 'price' + i
  call_historial = 'historial' + i
  call_delete = 'delete' + i

  if alert_array[int(i)] == False:
    keyboard = [[InlineKeyboardButton('🛒 Comprar producto', url=url_array[int(i)])],
                [InlineKeyboardButton('💰 Set target price', callback_data=call_target)],
                [InlineKeyboardButton('🚨 Alerta: OFF', callback_data=call_alarm)],
                [InlineKeyboardButton('💵 Precio del producto', callback_data=call_precio)],
                [InlineKeyboardButton('📈 Historial precios', callback_data=call_historial)],
                [InlineKeyboardButton('🗑️ Borrar producto', callback_data=call_delete)],
                [InlineKeyboardButton('🔙 Volver atras', callback_data='main')]]
  else:
    keyboard = [[InlineKeyboardButton('🛒 Comprar producto', url=url_array[int(i)])],
                [InlineKeyboardButton('💰 Set target price', callback_data=call_target)],
                [InlineKeyboardButton('🚨 Alerta: ON', callback_data=call_alarm)],
                [InlineKeyboardButton('💵 Precio del producto', callback_data=call_precio)],
                [InlineKeyboardButton('📈 Historial precios', callback_data=call_historial)],
                [InlineKeyboardButton('🗑️ Borrar producto', callback_data=call_delete)],
                [InlineKeyboardButton('🔙 Volver atras', callback_data='main')]]

  return InlineKeyboardMarkup(keyboard)

############################### Hable response ############################################
def handle_response(text: str) -> str:
    processed: str = text.lower()
    return 'I didnt understand'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text 

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    response: str = handle_response(text)

    print('Bot:', response)
    await update.message.reply_text(response)

async def error (update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'User {update} caused error {context.error}')

#GRAFICO #GRAFICO #GRAFICO #GRAFICO #GRAFICO 
#GRAFICO #GRAFICO #GRAFICO #GRAFICO #GRAFICO 
#GRAFICO #GRAFICO #GRAFICO #GRAFICO #GRAFICO 
#GRAFICO #GRAFICO #GRAFICO #GRAFICO #GRAFICO 
#GRAFICO #GRAFICO #GRAFICO #GRAFICO #GRAFICO 
    
if __name__ == '__main__':

    app = Application.builder().token(constant.API_KEY).build()
    
    # Configuración de la conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('track', track)],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nombre)],
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CallbackQueryHandler(main_menu, pattern='main'))
    app.add_handler(CallbackQueryHandler(sub_menu, pattern = 'm0'))
    app.add_handler(CallbackQueryHandler(cancel_menu, pattern = 'cancel_menu'))
    app.add_handler(CallbackQueryHandler(target_product, pattern='target'))
    app.add_handler(CallbackQueryHandler(alarm_product, pattern='alarm'))
    app.add_handler(CallbackQueryHandler(price_print, pattern='price'))
    app.add_handler(CallbackQueryHandler(history_product, pattern='historial'))
    app.add_handler(CallbackQueryHandler(delete_product, pattern='delete'))
    app.add_handler(CallbackQueryHandler(target_product, pattern='target'))
    
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_price_target))

    # Mensajes
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Error
    app.add_error_handler(error)

    job_queue = app.job_queue
    job_minute = job_queue.run_repeating(check_prices, interval=600, first=1)

    print("Polling ....")
    app.run_polling(allowed_updates=5)
