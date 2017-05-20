# -*- coding: utf-8 -*-
import telegram
from telegram.ext import Updater, CommandHandler, ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from emoji import emojize
from models import *
import config

bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
updater = Updater(config.TELEGRAM_TOKEN)

# Utils
def build_menu(buttons, n_cols):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    return menu

# Commands
def start(bot, update):
    # Check if messenger's chat id already exists
    chat_id = update.message.chat.id
    _from = update.message.from_user

    citizen = Citizen.where_has('channels',
        lambda ch: ch.where('account_id', chat_id)
                     .where('communication_type_id', CommunicationType.TELEGRAM)
    ).first()

    # If not create the citizen
    if citizen is None:
        Citizen.createForTelegram(chat_id, _from.first_name)
        message = u'Hola {}, Soy Hojita {} y te ayudaré a reportar casos de contaminación de forma anónima {}'.format(
            _from.first_name, emojize(':grinning_face:'), emojize(':winking_face:'))
    else:
        message = u'Hola {} {}'.format(citizen.name, emojize(':grinning_face:'))

    update.message.reply_text(message)

    message = u'Puedes comenzar un caso de contaminación usando el comando /reportar'

    update.message.reply_text(message)

def ask_for_new_case(bot, update):
    keyboard = [[InlineKeyboardButton('Si :)', callback_data='ask_for_cont_type'),
                 InlineKeyboardButton('NO :(', callback_data='nothing')]]

    update.message.reply_text(u'¿Deseas reportar un caso de contaminación? :o',
        reply_markup=InlineKeyboardMarkup(keyboard))

def ask_for_cont_type(bot, update):
    keyboard = []

    message = u'¡Genial! Primero necesito que selecciones el tipo de contaminación que más se parece a lo que deseas reportar :)'
    for cont_type in ContaminationType.all():
        keyboard.append(
            InlineKeyboardButton(u'{}'.format(cont_type.description),
                callback_data='new_case {}'.format(cont_type.id))
        )

    update.callback_query.message.reply_text(message,
        reply_markup=InlineKeyboardMarkup(build_menu(keyboard, n_cols=2)))

    return NEW_CASE

def new_case(bot, update):
    query = update.callback_query
    data = query.data.split()

    cont_type = ContaminationType.find(data[1])
    message = u'{}'.format(cont_type.description)

    query.message.reply_text(message)

    return ConversationHandler.END

def cancel(bot, update):
    return ConversationHandler.END

NEW_CASE, PHOTO = range(2)
# Handlers
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('reportar', ask_for_new_case))
updater.dispatcher.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(ask_for_cont_type, pattern='ask_for_cont_type')],
    states={
        NEW_CASE: [CallbackQueryHandler(new_case, pattern='new_case [0-9]')],
        PHOTO: [CallbackQueryHandler(new_case, pattern='new_case [0-9]')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
))
