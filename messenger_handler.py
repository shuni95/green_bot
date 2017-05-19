## Filename messenger_handler.py
# -*- coding: utf-8 -*-

import requests
from messenger import Messenger
from models import *

class MessengerHandler(object):
    chat_id = None

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def handle_bot(self, messaging):
        if 'postback' in messaging:
            self.handle_postback(messaging['postback']['payload'])
        elif 'message' in messaging:
            self.handle_message(messaging['message'])
        return 'ok'

    def handle_postback(self, payload):
        if payload == 'start':
            self.start()

        return 'ok'

    def handle_message(self, message):
        if 'quick_reply' in message:
            payload = message['quick_reply']['payload']
            args = payload.split()

            if args[0] == 'ask_for_cont_type':
                self.ask_for_cont_type()
            elif args[0] == 'nothing':
                self.nothing()
            elif args[0] == 'new_case':
                self.new_case(args[1])
            elif args[0] == 'report':
                self.report(args[1])

        elif 'text' in message:
            if message['text'] == 'reportar':
                self.ask_for_new_case()
            elif message['text'] == 'start':
                self.start()

        elif 'attachments' in message:
            # Check if exists a incomplete complaint
            citizen = Citizen.where_has('channels',
                lambda ch: ch.where('account_id', self.chat_id)).first()
            incomplete_complaint = citizen.complaints().incomplete().first()

            if incomplete_complaint is not None:
                if message['attachments'][0]['type'] == 'location':
                    self.add_location(incomplete_complaint, message['attachments'][0]['payload']['coordinates'])
                elif message['attachments'][0]['type'] == 'image':
                    self.add_images(incomplete_complaint, message['attachments'])
                else:
                    message = u'Por favor, no ingrese tipos de archivo que no se le han solicitado.'

                    Messenger.send_text(self.chat_id, message)
            else:
                if message['attachments'][0]['type'] == 'image':
                    message = u'Veo que has subido una imagen, disculpa pero primero debes decirme si quieres reportar un caso de contaminación.'
                    Messenger.send_text(self.chat_id, message)
                    self.ask_for_new_case()

    def start(self):
        # Check if messenger's chat id already exists
        citizen = Citizen.where_has('channels',
            lambda ch: ch.where('account_id', self.chat_id)).first()

        # If not create the citizen
        if citizen is None:
            user = Messenger.get_user_data(self.chat_id)

            Citizen.createForMessenger(self.chat_id, user)
            message = u'Hola {}, Soy Hojita :D y te ayudaré a reportar casos de contaminación de forma anónima ;)'.format(
                user['first_name'])
        # Else change the welcome message
        else:
            message = u'Hola {} :D'.format(citizen.name)

        Messenger.send_text(self.chat_id, message)

        self.ask_for_new_case()

    def ask_for_new_case(self):
        quick_replies = [
            {'content_type': 'text', 'title': 'Si :D', 'payload': 'ask_for_cont_type'},
            {'content_type': 'text', 'title': 'No :(', 'payload': 'nothing'}
        ]
        message = u'¿Deseas reportar un caso de contaminación? :o'

        Messenger.send_text(self.chat_id, message, quick_replies)

    def ask_for_cont_type(self):
        quick_replies = []
        message = u'¡Genial! Primero necesito que selecciones el tipo de contaminación que más se parece a lo que deseas reportar :)'

        for contamination_type in ContaminationType.all():
            quick_replies.append({
                'content_type': 'text',
                'title': contamination_type.description,
                'payload': 'new_case {}'.format(contamination_type.id)})

        Messenger.send_text(self.chat_id, message, quick_replies)

    def nothing(self):
        message = u'Bueno :(, pero no te olvides de avisarme cuándo veas un caso de contaminación :D'
        Messenger.send_text(self.chat_id, message)

    def new_case(self, cont_type):
        citizen = Citizen.where_has('channels',
            lambda ch: ch.where('account_id', self.chat_id)).first()

        complaint = Complaint()
        complaint.citizen_id = citizen.id
        complaint.type_contamination_id = cont_type
        complaint.type_communication_id = CommunicationType.MESSENGER
        complaint.complaint_state_id = ComplaintState.INCOMPLETE
        complaint.save()

        message = u'¡Excelente! Ahora necesito una foto sobre el caso de contaminación, si tienes más mejor :D pero solo puedo guardar hasta 3 :)'
        Messenger.send_text(self.chat_id, message)

    def add_images(self, incomplete_complaint, attachments):
        images = []
        for attachment in attachments:
            if attachment['type'] == 'image':
                images.append(ComplaintImage(img=attachment['payload']['url']))

        incomplete_complaint.images().save_many(images)
        message = u'¡Sigamos! Ahora necesito que envies la localización del lugar donde tomaste la foto. Si estas ahi selecciona ubicación actual :D'
        ask_location = [{
            "content_type": "location",
        }]

        Messenger.send_text(self.chat_id, message, ask_location)

    def add_location(self, incomplete_complaint, coordinates):
        incomplete_complaint.latitude = coordinates['lat']
        incomplete_complaint.longitude = coordinates['long']
        # To-Do
        # Get district name from google maps
        incomplete_complaint.save()

        message = u'¿Deseas agregar algún comentario?'
        quick_replies = [
            {
                'content_type': 'text', 'title': 'Si :D',
                'payload': 'ask_for_comment'},
            {
                'content_type': 'text', 'title': 'No, Gracias',
                'payload': 'report {}'.format(incomplete_complaint.id)
            }
        ]

        Messenger.send_text(self.chat_id, message, quick_replies)

    def report(self, complaint_id):
        incomplete_complaint = Complaint.find(complaint_id)
        incomplete_complaint.complaint_state_id = ComplaintState.COMPLETE
        incomplete_complaint.save()

        message = u'¡Gracias por tu ayuda! Acabó de registrar tu caso de contaminación :D'
        Messenger.send_text(self.chat_id, message)

        citizen = Citizen.where_has('channels',
                lambda ch: ch.where('account_id', self.chat_id)).first()

        if citizen.complaints.count() == 1:
            message = u'Te enviaré actualizaciones sobre las actividades que realice la municipalidad :) asi que por favor no borres este chat :D'
            Messenger.send_text(self.chat_id, message)
            message = u'Para futuros reportes de contaminación puedes usar el menú o escribe "reportar" :3'
            Messenger.send_text(self.chat_id, message)
        else:
            message = u'Recuerda que te enviaré actualizaciones sobre tu caso :) asi que por favor no borres este chat :D'
            Messenger.send_text(self.chat_id, message)
