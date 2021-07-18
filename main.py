import telebot
from telegraph import Telegraph
import markdown
import params

bot = telebot.TeleBot(params.token)
telegraph = Telegraph(params.telegraph_token)


def htmlify_text_message(message):
    try:
        if message.json['forward_from'] is not None:
            s = "###" + message.json['forward_from']['first_name']
            author = markdown.markdown(s)
        else:
            s = "###" + message.json['from']['first_name']
            author = markdown.markdown(s)
        text = markdown.markdown(message.json.get('text'))
        print(author + text)
        return author + text
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "Что-то пошло не так, повторите запрос")


class Sender:
    current_name = None
    current_state = params.IDLE
    current_html = ""


sender = Sender()


@bot.message_handler(commands=['start', 'help'])
def command_help(message):
    text = "Этот бот позволяет сохранять пересланные сообщения в формате telegraph-статьи.\n" \
           "Введите /auth, чтобы создать пользователя. \n" \
           "Введите /newpage, чтобы создать новую страницу или отредактировать уже существующую," \
           " далее перешлите сообщения, которые хотите на нее добавить. \n" \
           "Введите /create, чтобы сохранить страницу, в следующем сообщении введите заголовок этой страницы. \n" \
           "Введите /edit, чтобы добавить сообщения на уже созданную страницу, в следующем сообщении" \
           "напишите название этой страницы (названием является все после / в url-адресе страницы). \n" \
           "Введите /pages, чтобы вывести список всех ваших страниц. \n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['auth'])
def command_auth(message):
    sender.current_state = params.ACCOUNT
    text = '''Введите имя аккаунта:'''
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['newpage'])
def command_newpage(message):
    print(message)
    if sender.current_name is None:
        bot.send_message(message.chat.id, "Вы еще не создали пользователя!")
        return
    sender.current_state = params.WRITING


@bot.message_handler(commands=['create'])
def command_create(message):
    print(message)
    sender.current_state = params.CREATEPAGE


@bot.message_handler(commands=['pages'])
def command_pages(message):
    pages = telegraph.get_page_list()
    text = ""
    for page in pages['pages']:
        text += page['url'] + '\n'
    if len(text) == 0:
        text = "Вы еще не создавали telegraph-страницы"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['edit'])
def command_edit(message):
    sender.current_state = params.EDIT


@bot.message_handler(func=lambda message: True, content_types='text')
def handler(message):
    print(message)
    if sender.current_state == params.IDLE:
        return
    if sender.current_state == params.ACCOUNT:
        sender.current_name = message.json.get('text')
        sender.current_state = params.IDLE
        bot.send_message(message.chat.id, f"Создан аккаунт с именем {sender.current_name}")
        return
    if sender.current_state == params.WRITING:
        sender.current_html += htmlify_text_message(message)
        return
    if sender.current_state == params.CREATEPAGE:
        print(sender.current_html)
        response = telegraph.create_page(title=message.json.get('text'),
                                         author_name=sender.current_name,
                                         html_content=sender.current_html)
        sender.current_html = ""
        sender.current_state = params.IDLE
        bot.send_message(message.chat.id, text='https://telegra.ph/{}'.format(response['path']))
        return
    if sender.current_state == params.EDIT:
        print(sender.current_html)
        response = telegraph.get_page(path=message.json.get('text'))
        current_content = response['content']
        current_title = response['title']
        response = telegraph.edit_page(path=message.json.get('text'),
                                       title=current_title,
                                       html_content=current_content + sender.current_html)
        sender.current_html = ""
        sender.current_state = params.IDLE
        bot.send_message(message.chat.id, text='https://telegra.ph/{}'.format(response['path']))


bot.polling()
