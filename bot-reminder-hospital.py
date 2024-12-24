import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from telegram.constants import ParseMode


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


scheduler = BackgroundScheduler()
scheduler.start()


OWNER_ID = '833830825'
patients = []


pending_answers = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if str(user_id) == OWNER_ID:
        await update.message.reply_text('Добро пожаловать, владелец! Используйте /set_reminder, чтобы установить напоминания для своих пациентов.')
    else:
        await update.message.reply_text('Здравствуйте! Вы будете получать напоминания о необходимости сообщить о своем самочувствии.')


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if str(user_id) != OWNER_ID:
        await update.message.reply_text('Вы не имеете права устанавливать напоминания.')
        return

    try:
        if len(context.args) < 2:
            raise ValueError("Недостаточно аргументов. Используйте: /set_reminder YYYY-MM-DD HH:MM:SS")

        time_str = context.args[0] + " " + context.args[1]
        reminder_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

        scheduler.add_job(send_reminder, trigger=DateTrigger(run_date=reminder_time), args=[context])

        await update.message.reply_text(f'Напоминание установлено на: {reminder_time}')
    except ValueError as e:
        await update.message.reply_text(f'Ошибка: {str(e)}')


async def register_patient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if str(user_id) != OWNER_ID:
        await update.message.reply_text('Вы не имеете права регистрировать пациентов.')
        return

    if not context.args:
        await update.message.reply_text('Используйте: /register_patient patient_telegram_id')
        return

    patient_id = context.args[0]
    patients.append(patient_id)
    await update.message.reply_text(f'Пациент {patient_id} зарегистрирован.')


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    question = "Как Вы себя чувствуете?"
    for patient_id in patients:
        try:
            await context.bot.send_message(chat_id=patient_id, text=question)
            pending_answers[patient_id] = question
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения {patient_id}: {e}")

async def schedule_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, reminder_time: datetime) -> None:
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_time),
        args=[context]
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in pending_answers:
        question = pending_answers.pop(user_id)
        answer = update.message.text
        response = f'Пациент {user_id} ответил на: "{question}": {answer}'
        await context.bot.send_message(chat_id=OWNER_ID, text=response)


def main() -> None:
    application = ApplicationBuilder().token("").build()


    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_reminder", set_reminder))
    application.add_handler(CommandHandler("register_patient", register_patient))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


    application.run_polling()


if __name__ == '__main__':
    main()
