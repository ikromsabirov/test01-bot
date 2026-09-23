from aiogram.exceptions import TelegramNetworkError
import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

import config
from database import *
from keyboards import *
from excel_parser import parse_excel

logging.basicConfig(level=logging.INFO)

# === PROXY (PythonAnywhere uchun) ===
# Render'da proxy kerak emas
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class UserStates(StatesGroup):
    waiting_full_name = State()
    waiting_class = State()
    waiting_subject = State()
    waiting_test = State()
    answering = State()
    waiting_rating_test = State()
    waiting_other_class = State()
    waiting_other_subject = State()
    waiting_other_test = State()


class AdminStates(StatesGroup):
    waiting_class_for_subject = State()
    waiting_subject_name = State()
    waiting_test_class = State()
    waiting_test_subject = State()
    waiting_test_name = State()
    waiting_excel_file = State()
    waiting_delete_test = State()
    waiting_rating_class = State()
    waiting_rating_subject = State()
    waiting_rating_clear_confirm = State()
    edit_test_class = State()
    edit_test_subject = State()
    edit_test_select = State()
    edit_question_select = State()
    edit_question_field = State()
    edit_question_value = State()
    edit_add_question = State()
    edit_question_image = State()          # ← YANGI
    edit_question_image_upload = State()


init_db()

async def send_with_retry(func, *args, max_retries=3, **kwargs):
    """
    Xabar yuborishni qayta urinish bilan bajaradi.
    ProxyError yoki TelegramNetworkError bo'lsa, 3 marta qayta urinadi.
    """
    delays = [1, 2, 4]  # Kutish vaqtlari (soniya)
    last_error = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (TelegramNetworkError, Exception) as e:
            error_name = type(e).__name__
            # Faqat tarmoq xatoliklarini qayta urinish
            if 'Proxy' in error_name or 'Network' in error_name or '503' in str(e) or 'Connector' in error_name:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                    continue
            raise  # Boshqa xatoliklar uchun darhol qaytaramiz

    if last_error:
        raise last_error


# ================= /start =================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in config.ADMIN_IDS:
        await message.answer("Admin sifatida xush kelibsiz!", reply_markup=admin_panel_keyboard())
    else:
        user = get_user(user_id)
        if user is None:
            await message.answer("Iltimos, to'liq ismingizni kiriting (Familiya Ism):")
            await state.set_state(UserStates.waiting_full_name)
        else:
            await message.answer("Xush kelibsiz!", reply_markup=main_menu_keyboard(is_admin=False))


@dp.message(UserStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    try:
        full_name = message.text.strip()
        if len(full_name) < 3:
            await message.answer("Iltimos, to'liq ismingizni kiriting (Familiya Ism):")
            return
        add_user(message.from_user.id, full_name)
        classes = get_classes()
        await message.answer(f"Rahmat, {full_name}! Endi sinfingizni tanlang:",
                             reply_markup=class_selection_keyboard(classes))
        await state.set_state(UserStates.waiting_class)
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {str(e)}")


@dp.message(UserStates.waiting_class)
async def process_user_class(message: Message, state: FSMContext):
    class_name = message.text
    classes = get_classes()
    for cls in classes:
        if cls['name'] == class_name:
            update_user_class(message.from_user.id, cls['id'])
            await message.answer(f"Sinf: {class_name} saqlandi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return
    await message.answer("Iltimos, ro'yxatdan sinf tanlang:",
                         reply_markup=class_selection_keyboard(classes))


# ================= TEST ISHLASH =================
@dp.message(F.text == "📝 Test ishlash")
async def start_test_flow(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not user['class_id']:
        await message.answer("Avval ro'yxatdan o'ting. /start bosing")
        return
    subjects = get_subjects_by_class(user['class_id'])
    if not subjects:
        await message.answer("Bu sinf uchun fanlar qo'shilmagan")
        return
    buttons = [[KeyboardButton(text=subj['name'])] for subj in subjects]
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await message.answer("Fanni tanlang:",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(UserStates.waiting_subject)


@dp.message(UserStates.waiting_subject)
async def process_subject_selection(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    user = get_user(message.from_user.id)
    subjects = get_subjects_by_class(user['class_id'])
    selected_subject = None
    for subj in subjects:
        if subj['name'] == message.text:
            selected_subject = subj
            break
    if not selected_subject:
        await message.answer("Iltimos, fanlardan birini tanlang")
        return
    await state.update_data(subject_id=selected_subject['id'])
    tests = get_tests_by_subject(selected_subject['id'])
    if not tests:
        await message.answer("Bu fan uchun testlar qo'shilmagan")
        return
    buttons = [[KeyboardButton(text=test['name'])] for test in tests]
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await message.answer("Testni tanlang:",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(UserStates.waiting_test)


@dp.message(UserStates.waiting_test)
async def process_test_selection(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    data = await state.get_data()
    subject_id = data['subject_id']
    tests = get_tests_by_subject(subject_id)
    selected_test = None
    for test in tests:
        if test['name'] == message.text:
            selected_test = test
            break
    if not selected_test:
        await message.answer("Iltimos, testlardan birini tanlang")
        return
    questions = get_questions_by_test(selected_test['id'])
    if not questions:
        await message.answer("Bu testda savollar yo'q")
        return
    shuffled_questions = []
    for q in questions:
        q_dict = dict(q)
        q_dict = shuffle_question_options(q_dict)
        shuffled_questions.append(q_dict)
    await state.update_data(test_id=selected_test['id'], questions=shuffled_questions,
                            current_index=0, score=0)
    await message.answer(
        "⚠️ DIQQAT!\n\nTest savollari himoyalangan. Ularni nusxalash, "
        "forward qilish yoki saqlash mumkin emas.\n\nTestni boshlaymiz!",
        protect_content=True
    )
    await ask_question(message, state)


# ================= BOSHQA SINF TESTLARI =================
@dp.message(F.text == "🔍 Boshqa sinf testlari")
async def start_other_class_flow(message: Message, state: FSMContext):
    await message.answer("Qaysi sinf testlarini ishlamoqchisiz?",
                         reply_markup=class_selection_keyboard(get_classes()))
    await state.set_state(UserStates.waiting_other_class)


@dp.message(UserStates.waiting_other_class)
async def process_other_class(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    classes = get_classes()
    selected = None
    for cls in classes:
        if cls['name'] == message.text:
            selected = cls
            break
    if not selected:
        await message.answer("Iltimos, sinfni ro'yxatdan tanlang")
        return
    subjects = get_subjects_by_class(selected['id'])
    if not subjects:
        await message.answer("Bu sinf uchun fanlar qo'shilmagan")
        return
    buttons = [[KeyboardButton(text=s['name'])] for s in subjects]
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await state.update_data(other_class_id=selected['id'], other_class_name=selected['name'])
    await message.answer("Fanni tanlang:",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(UserStates.waiting_other_subject)


@dp.message(UserStates.waiting_other_subject)
async def process_other_subject(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Sinfni tanlang:",
                             reply_markup=class_selection_keyboard(get_classes()))
        await state.set_state(UserStates.waiting_other_class)
        return
    data = await state.get_data()
    class_id = data['other_class_id']
    subjects = get_subjects_by_class(class_id)
    selected = None
    for s in subjects:
        if s['name'] == message.text:
            selected = s
            break
    if not selected:
        await message.answer("Fanni ro'yxatdan tanlang")
        return
    tests = get_tests_by_subject(selected['id'])
    if not tests:
        await message.answer("Bu fan uchun testlar qo'shilmagan")
        return
    buttons = [[KeyboardButton(text=t['name'])] for t in tests]
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await state.update_data(other_subject_id=selected['id'])
    await message.answer("Testni tanlang:",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(UserStates.waiting_other_test)


@dp.message(UserStates.waiting_other_test)
async def process_other_test(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        data = await state.get_data()
        class_id = data.get('other_class_id')
        subjects = get_subjects_by_class(class_id)
        buttons = [[KeyboardButton(text=s['name'])] for s in subjects]
        buttons.append([KeyboardButton(text="🔙 Orqaga")])
        await message.answer("Fanni tanlang:",
                             reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        await state.set_state(UserStates.waiting_other_subject)
        return
    data = await state.get_data()
    subject_id = data['other_subject_id']
    tests = get_tests_by_subject(subject_id)
    selected = None
    for t in tests:
        if t['name'] == message.text:
            selected = t
            break
    if not selected:
        await message.answer("Testni ro'yxatdan tanlang")
        return
    questions = get_questions_by_test(selected['id'])
    if not questions:
        await message.answer("Bu testda savollar yo'q")
        return
    shuffled_questions = []
    for q in questions:
        q_dict = dict(q)
        q_dict = shuffle_question_options(q_dict)
        shuffled_questions.append(q_dict)
    await state.update_data(test_id=selected['id'], questions=shuffled_questions,
                            current_index=0, score=0)
    await message.answer(
        "⚠️ DIQQAT!\n\nTest savollari himoyalangan. Ularni nusxalash, "
        "forward qilish yoki saqlash mumkin emas.\n\nTestni boshlaymiz!",
        protect_content=True
    )
    await ask_question(message, state)


# ================= SAVOL BERISH VA JAVOB =================
def shuffle_question_options(question):
    if question['type'] not in ['closed', 'yopiq']:
        return question
    options = []
    for letter in ['A', 'B', 'C', 'D']:
        text = question.get(f'option_{letter.lower()}', '')
        if text:
            options.append((letter, text))
    if not options:
        return question
    original_correct = question['correct_answer'].upper()
    shuffled = options[:]
    random.shuffle(shuffled)
    new_letters = ['A', 'B', 'C', 'D']
    for i, (old_letter, text) in enumerate(shuffled):
        if i < 4:
            question[f'option_{new_letters[i].lower()}'] = text
            if old_letter == original_correct:
                question['correct_answer'] = new_letters[i]
    for j in range(len(shuffled), 4):
        question[f'option_{new_letters[j].lower()}'] = ''
    return question


async def ask_question(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    index = data['current_index']
    if index >= len(questions):
        await finish_test(message, state)
        return
    question = questions[index]

    # === RASM BOR BO'LSA, AVVAL UNI YUBORAMIZ ===
    image_file_id = question.get('image_file_id')
    if image_file_id:
        try:
            await send_with_retry(
                message.answer_photo,
                photo=image_file_id,
                caption=f"🖼 Savol {index+1}/{len(questions)} rasmi",
                protect_content=True
            )
        except Exception:
            pass  # Rasm yuborilmasa, davom etamiz

    if question['type'] in ['closed', 'yopiq']:
        options = []
        if question['option_a']:
            options.append(f"A) {question['option_a']}")
        if question['option_b']:
            options.append(f"B) {question['option_b']}")
        if question['option_c']:
            options.append(f"C) {question['option_c']}")
        if question['option_d']:
            options.append(f"D) {question['option_d']}")
        text = f"Savol {index+1}/{len(questions)}:\n{question['question_text']}\n\n" + "\n".join(options)
        await send_with_retry(
            message.answer,
            text,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="A")], [KeyboardButton(text="B")],
                          [KeyboardButton(text="C")], [KeyboardButton(text="D")]],
                resize_keyboard=True
            ),
            protect_content=True
        )
    else:
        await send_with_retry(
            message.answer,
            f"Savol {index+1}/{len(questions)}:\n{question['question_text']}\n\nJavobingizni yozing:",
            reply_markup=back_keyboard(),
            protect_content=True
        )
    await state.set_state(UserStates.answering)


# ================= JAVOBNI QAYTA ISHLASH (LOCK BILAN) =================
import asyncio

# Har bir foydalanuvchi uchun qulf
_user_locks = {}

def get_user_lock(user_id):
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


"""@dp.message(UserStates.answering)
async def process_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lock = get_user_lock(user_id)

    # Agar oldingi javob hali qayta ishlanayotgan bo'lsa — kutmasdan qaytamiz
    if lock.locked():
        return

    async with lock:
        data = await state.get_data()
        questions = data.get('questions')
        if not questions:
            await state.clear()
            return

        index = data.get('current_index', 0)
        if index >= len(questions):
            await finish_test(message, state)
            return

        question = questions[index]
        user_answer = (message.text or "").strip()

        # === YOPIQ SAVOL: faqat A/B/C/D qabul qilinadi ===
        if question['type'] in ['closed', 'yopiq']:
            if user_answer.upper() not in ['A', 'B', 'C', 'D']:
                await message.answer(
                    "Iltimos, faqat A, B, C yoki D tugmalaridan birini bosing.",
                    protect_content=True
                )
                return
            correct = question['correct_answer'].upper()
            is_correct = user_answer.upper() == correct
            if is_correct:
                data['score'] = data.get('score', 0) + 1
        else:
            # === OCHIQ SAVOL ===
            correct = question['correct_answer'].strip().lower()
            is_correct = user_answer.lower() == correct
            if is_correct:
                data['score'] = data.get('score', 0) + 1

        # === Javob haqida xabar berish ===
        if question['type'] in ['closed', 'yopiq']:
            if is_correct:
                await message.answer("✅ To'g'ri!", protect_content=True)
            else:
                await message.answer(
                    f"❌ Noto'g'ri. To'g'ri javob: {question['correct_answer']}",
                    protect_content=True
                )

        # === Keyingi savolga o'tish ===
        data['current_index'] = index + 1
        await state.update_data(**data)
        await ask_question(message, state)"""


# ================= JAVOBNI QAYTA ISHLASH =================
@dp.message(UserStates.answering)
async def process_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lock = get_user_lock(user_id)

    # Agar oldingi javob hali qayta ishlanayotgan bo'lsa — kutmasdan qaytamiz
    if lock.locked():
        return

    async with lock:
        data = await state.get_data()
        questions = data.get('questions')
        if not questions:
            await state.clear()
            return

        index = data.get('current_index', 0)
        if index >= len(questions):
            await finish_test(message, state)
            return

        question = questions[index]
        user_answer = (message.text or "").strip()

        # === YOPIQ SAVOL: faqat A/B/C/D qabul qilinadi ===
        if question['type'] in ['closed', 'yopiq']:
            if user_answer.upper() not in ['A', 'B', 'C', 'D']:
                await message.answer(
                    "Iltimos, faqat A, B, C yoki D tugmalaridan birini bosing.",
                    protect_content=True
                )
                return
            correct = question['correct_answer'].upper()
            is_correct = user_answer.upper() == correct
        else:
            # === OCHIQ SAVOL ===
            correct = question['correct_answer'].strip()
            is_correct = user_answer.strip().lower() == correct.lower()

        # Ball qo'shish
        if is_correct:
            data['score'] = data.get('score', 0) + 1

        # === JAVOBLAR TARIXINI SAQLASH ===
        history = data.get('answers_history', [])
        history.append({
            'index': index + 1,
            'question_text': question['question_text'],
            'user_answer': user_answer,
            'correct_answer': correct,
            'is_correct': is_correct,
            'type': question['type']
        })
        data['answers_history'] = history

        # === Keyingi savolga o'tish (FEEDBACKSIZ) ===
        data['current_index'] = index + 1
        await state.update_data(**data)
        await ask_question(message, state)

"""async def finish_test(message: Message, state: FSMContext):
    data = await state.get_data()
    total = len(data['questions'])
    score = data['score']
    percentage = (score / total) * 100 if total > 0 else 0
    test_id = data['test_id']
    user_id = message.from_user.id
    save_result(user_id, test_id, score, total, percentage)
    await message.answer(
        f"Test yakunlandi!\n\nTo'g'ri javoblar: {score}/{total}\nFoiz: {percentage:.1f}%",
        reply_markup=main_menu_keyboard(),
        protect_content=True
    )
    await state.clear()


# ================= REYTING (O'QUVCHI) =================
@dp.message(F.text == "📊 Reyting")
async def show_user_rating(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    try:
        user_results = get_user_results(user_id)
    except Exception as e:
        await message.answer(f"Xatolik: {e}")
        return
    if not user_results:
        await message.answer("Siz hali test ishlamagansiz. Avval test ishlang.")
        return
    test_ids = []
    for r in user_results:
        if r['test_id'] not in test_ids:
            test_ids.append(r['test_id'])
    buttons = []
    for test_id in test_ids:
        test_info = next(r for r in user_results if r['test_id'] == test_id)
        buttons.append([KeyboardButton(text=test_info['test_name'])])
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await message.answer("Qaysi test bo'yicha reytingni ko'rmoqchisiz?",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(UserStates.waiting_rating_test)


@dp.message(UserStates.waiting_rating_test)
async def process_rating_test_selection(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    user_id = message.from_user.id
    test_name = message.text
    try:
        user_results = get_user_results(user_id)
    except Exception as e:
        await message.answer(f"Xatolik: {e}")
        await state.clear()
        return
    selected_test_id = None
    for r in user_results:
        if r['test_name'] == test_name:
            selected_test_id = r['test_id']
            break
    if selected_test_id is None:
        await message.answer("Test topilmadi, qaytadan tanlang")
        return
    best_results = get_test_best_results(selected_test_id)
    if not best_results:
        await message.answer("Bu test bo'yicha natijalar yo'q")
        await state.clear()
        return
    text = f"📊 {test_name} bo'yicha reyting:\n\n"
    for idx, row in enumerate(best_results, start=1):
        bp = row['best_percentage'] if row['best_percentage'] is not None else 0
        full_name = row['full_name'] if row['full_name'] else "Noma'lum"
        text += f"{idx}-o'rin {full_name} ({bp:.1f}%)\n"
    await message.answer(text, reply_markup=main_menu_keyboard())
    await state.clear()"""
async def finish_test(message: Message, state: FSMContext):
    data = await state.get_data()
    total = len(data['questions'])
    score = data['score']
    percentage = (score / total) * 100 if total > 0 else 0
    test_id = data['test_id']
    user_id = message.from_user.id
    history = data.get('answers_history', [])

    save_result(user_id, test_id, score, total, percentage)

    # === UMUMIY NATIJA ===
    if percentage >= 80:
        emoji = "🎉"
        baho = "A'lo"
    elif percentage >= 60:
        emoji = "👍"
        baho = "Yaxshi"
    elif percentage >= 40:
        emoji = "📖"
        baho = "Qoniqarli"
    else:
        emoji = "📚"
        baho = "Qoniqarsiz"

    summary = (
        f"{emoji} Test yakunlandi!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ To'g'ri: {score}/{total}\n"
        f"❌ Noto'g'ri: {total - score}/{total}\n"
        f"📊 Foiz: {percentage:.1f}%\n"
        f"🏅 Baho: {baho}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(summary, reply_markup=main_menu_keyboard(), protect_content=True)

    # === HAR BIR SAVOL BO'YICHA BATAFSIL ===
    if history:
        detail = "📋 Savollar bo'yicha tahlil:\n\n"
        for h in history:
            if h['is_correct']:
                mark = "✅"
            else:
                mark = "❌"

            # Savol matnini qisqartirish
            q_text = h['question_text']
            if len(q_text) > 50:
                q_text = q_text[:50] + "..."

            detail += f"{mark} {h['index']}. {q_text}\n"

            if h['type'] in ['closed', 'yopiq']:
                detail += f"    Sizning javob: {h['user_answer'].upper()}\n"
                if not h['is_correct']:
                    detail += f"    To'g'ri javob: {h['correct_answer'].upper()}\n"
            else:
                if not h['is_correct']:
                    user_ans = h['user_answer']
                    if len(user_ans) > 40:
                        user_ans = user_ans[:40] + "..."
                    correct_ans = h['correct_answer']
                    if len(correct_ans) > 40:
                        correct_ans = correct_ans[:40] + "..."
                    detail += f"    Sizning javob: {user_ans}\n"
                    detail += f"    To'g'ri javob: {correct_ans}\n"
            detail += "\n"

        # Xabar juda uzun bo'lsa, bo'lib yuboramiz
        if len(detail) > 4000:
            chunks = [detail[i:i+4000] for i in range(0, len(detail), 4000)]
            for chunk in chunks:
                await message.answer(chunk, protect_content=True)
        else:
            await message.answer(detail, protect_content=True)

    await state.clear()


# ================= ADMIN PANEL =================
@dp.message(F.text == "👨‍💼 Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Admin panel", reply_markup=admin_panel_keyboard())


@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in config.ADMIN_IDS:
        await message.answer("Admin panel", reply_markup=admin_panel_keyboard())
    else:
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard())


@dp.message(F.text == "🏠 Bosh menyu")
async def go_home(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in config.ADMIN_IDS:
        await message.answer("Admin panel", reply_markup=admin_panel_keyboard())
    else:
        await message.answer("Bosh menyu", reply_markup=main_menu_keyboard(is_admin=False))


# ================= FAN QO'SHISH =================
@dp.message(F.text == "➕ Fan qo'shish")
async def add_subject_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Qaysi sinfga fan qo'shasiz?", reply_markup=class_selection_keyboard(get_classes()))
    await state.set_state(AdminStates.waiting_class_for_subject)


@dp.message(AdminStates.waiting_class_for_subject)
async def process_class_for_subject(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    classes = get_classes()
    for cls in classes:
        if cls['name'] == message.text:
            await state.update_data(class_id=cls['id'])
            await message.answer("Fan nomini kiriting:", reply_markup=back_keyboard())
            await state.set_state(AdminStates.waiting_subject_name)
            return
    await message.answer("Iltimos, sinfni to'g'ri tanlang")


@dp.message(AdminStates.waiting_subject_name)
async def process_subject_name(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    data = await state.get_data()
    class_id = data['class_id']
    subject_name = message.text.strip()
    add_subject(class_id, subject_name)
    await message.answer(f"'{subject_name}' fani qo'shildi!", reply_markup=admin_panel_keyboard())
    await state.clear()


# ================= TEST QO'SHISH =================
@dp.message(F.text == "📋 Test qo'shish")
async def add_test_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Qaysi sinfga test qo'shasiz?", reply_markup=class_selection_keyboard(get_classes()))
    await state.set_state(AdminStates.waiting_test_class)


@dp.message(AdminStates.waiting_test_class)
async def process_test_class(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    classes = get_classes()
    for cls in classes:
        if cls['name'] == message.text:
            await state.update_data(class_id=cls['id'])
            subjects = get_subjects_by_class(cls['id'])
            if not subjects:
                await message.answer("Bu sinfda fanlar yo'q. Avval fan qo'shing.")
                await state.clear()
                return
            buttons = [[KeyboardButton(text=s['name'])] for s in subjects]
            buttons.append([KeyboardButton(text="🔙 Orqaga")])
            await message.answer("Fanni tanlang:",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
            await state.set_state(AdminStates.waiting_test_subject)
            return
    await message.answer("Sinf topilmadi")


@dp.message(AdminStates.waiting_test_subject)
async def process_test_subject(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    data = await state.get_data()
    class_id = data['class_id']
    subjects = get_subjects_by_class(class_id)
    for subj in subjects:
        if subj['name'] == message.text:
            await state.update_data(subject_id=subj['id'])
            await message.answer("Test nomini kiriting:", reply_markup=back_keyboard())
            await state.set_state(AdminStates.waiting_test_name)
            return
    await message.answer("Fan topilmadi")


@dp.message(AdminStates.waiting_test_name)
async def process_test_name(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    test_name = message.text.strip()
    await state.update_data(test_name=test_name)
    await message.answer("Endi Excel faylni yuboring (.xlsx).", reply_markup=back_keyboard())
    await state.set_state(AdminStates.waiting_excel_file)


@dp.message(AdminStates.waiting_excel_file)
async def process_excel_file(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    if not message.document:
        await message.answer("Iltimos, Excel fayl yuboring (.xlsx)")
        return
    if not message.document.file_name.endswith('.xlsx'):
        await message.answer("Fayl .xlsx formatida bo'lishi kerak")
        return
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    downloaded_file = await bot.download_file(file_path)
    temp_file = f"temp_{message.from_user.id}.xlsx"
    with open(temp_file, 'wb') as f:
        f.write(downloaded_file.read())
    data = await state.get_data()
    subject_id = data['subject_id']
    test_name = data['test_name']
    test_id = add_test(subject_id, test_name)
    try:
        count = parse_excel(temp_file, test_id)
        await message.answer(f"Test muvaffaqiyatli yaratildi! {count} ta savol qo'shildi.",
                             reply_markup=admin_panel_keyboard())
        await state.clear()
    except Exception as e:
        delete_test(test_id)
        await message.answer(f"Xatolik yuz berdi: {str(e)}\nTest yaratilmadi.",
                             reply_markup=admin_panel_keyboard())
        await state.clear()
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# ================= TEST O'CHIRISH =================
@dp.message(F.text == "🗑 Test o'chirish")
async def delete_test_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    tests = get_all_tests()
    if not tests:
        await message.answer("Testlar mavjud emas")
        return
    text = "O'chirish uchun test ID sini kiriting:\n\n"
    for t in tests:
        text += f"ID: {t['id']} - {t['name']} ({t['subject_name']}, {t['class_name']})\n"
    await message.answer(text, reply_markup=back_keyboard())
    await state.set_state(AdminStates.waiting_delete_test)


@dp.message(AdminStates.waiting_delete_test)
async def process_delete_test(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    try:
        test_id = int(message.text)
        delete_test(test_id)
        await message.answer("Test o'chirildi!", reply_markup=admin_panel_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, test ID sini raqam bilan kiriting")


# ================= ADMIN REYTING =================
@dp.message(F.text == "📊 Reyting ko'rish")
async def admin_rating_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Qaysi sinf reytingini ko'rasiz?",
                         reply_markup=class_selection_keyboard(get_classes()))
    await state.set_state(AdminStates.waiting_rating_class)


@dp.message(AdminStates.waiting_rating_class)
async def process_admin_rating(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    classes = get_classes()
    for cls in classes:
        if cls['name'] == message.text:
            subjects = get_subjects_by_class(cls['id'])
            if not subjects:
                await message.answer(f"{cls['name']} uchun fanlar yo'q")
                return
            buttons = [[KeyboardButton(text=subj['name'])] for subj in subjects]
            buttons.append([KeyboardButton(text="🔙 Orqaga")])
            await state.update_data(rating_class_id=cls['id'], rating_class_name=cls['name'])
            await message.answer(f"{cls['name']} uchun fanni tanlang:",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
            await state.set_state(AdminStates.waiting_rating_subject)
            return
    await message.answer("Sinf topilmadi")


@dp.message(AdminStates.waiting_rating_subject)
async def process_admin_rating_subject(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    data = await state.get_data()
    class_id = data.get('rating_class_id')
    class_name = data.get('rating_class_name')
    if not class_id:
        await message.answer("Xatolik: sinf tanlanmagan. Qaytadan boshlang.")
        await state.clear()
        return
    subjects = get_subjects_by_class(class_id)
    selected_subject = None
    for subj in subjects:
        if subj['name'] == message.text:
            selected_subject = subj
            break
    if not selected_subject:
        await message.answer("Fan topilmadi, qaytadan tanlang")
        return
    await state.update_data(
        rating_subject_id=selected_subject['id'],
        rating_subject_name=selected_subject['name']
    )
    rating = get_rating_by_subject(selected_subject['id'])
    total_results = count_results_by_subject(selected_subject['id'])
    if not rating or total_results == 0:
        await message.answer(
            f"📊 {class_name} | {selected_subject['name']} fanidan reyting:\n\n"
            f"❌ Hali bu fan bo'yicha natijalar yo'q.",
            reply_markup=rating_actions_keyboard(),
            protect_content=True
        )
        await state.set_state(AdminStates.waiting_rating_clear_confirm)
        return
    text = f"📊 {class_name} | {selected_subject['name']} fanidan reyting:\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    shown = 0
    for row in rating:
        if row['tests_taken'] == 0:
            continue
        shown += 1
        avg = row['avg_percentage'] if row['avg_percentage'] is not None else 0
        total = row['total_score'] if row['total_score'] is not None else 0
        full_name = row['full_name'] if row['full_name'] else "Noma'lum"
        medal = ""
        if shown == 1:
            medal = "🥇 "
        elif shown == 2:
            medal = "🥈 "
        elif shown == 3:
            medal = "🥉 "
        text += f"{medal}{shown}. {full_name}\n"
        text += f"    📈 O'rtacha: {avg:.1f}% | Testlar: {row['tests_taken']} | Ball: {total}\n"
    if shown == 0:
        text += "❌ Hali bu fan bo'yicha natijalar yo'q.\n"
    text += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📋 Jami natijalar: {total_results} ta"
    await message.answer(text, reply_markup=rating_actions_keyboard(), protect_content=True)
    await state.set_state(AdminStates.waiting_rating_clear_confirm)


# ================= REYTINGNI TOZALASH =================
@dp.message(AdminStates.waiting_rating_clear_confirm, F.text == "🗑 Reytingni tozalash")
async def rating_clear_request(message: Message, state: FSMContext):
    data = await state.get_data()
    subject_id = data.get('rating_subject_id')
    subject_name = data.get('rating_subject_name', '')
    class_name = data.get('rating_class_name', '')
    if not subject_id:
        await message.answer("Xatolik: fan aniqlanmadi")
        await state.clear()
        return
    total = count_results_by_subject(subject_id)
    await message.answer(
        f"⚠️ DIQQAT!\n\n"
        f"📊 {class_name} | {subject_name}\n"
        f"🗑 Jami {total} ta natija o'chiriladi.\n\n"
        f"Bu amalni ORQAGA QAYTARIB BO'LMAYDI!\n\n"
        f"Davom etishni xohlaysizmi?",
        reply_markup=rating_clear_confirm_keyboard()
    )


@dp.message(AdminStates.waiting_rating_clear_confirm, F.text == "✅ Ha, tozalash")
async def rating_clear_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    subject_id = data.get('rating_subject_id')
    subject_name = data.get('rating_subject_name', '')
    class_name = data.get('rating_class_name', '')
    if not subject_id:
        await message.answer("Xatolik: fan aniqlanmadi")
        await state.clear()
        return
    try:
        deleted = delete_results_by_subject(subject_id)
        await message.answer(
            f"✅ Tozalandi!\n\n"
            f"📊 {class_name} | {subject_name}\n"
            f"🗑 O'chirilgan natijalar: {deleted} ta\n\n"
            f"Endi bu fan bo'yicha reyting bo'sh.",
            reply_markup=admin_panel_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}", reply_markup=admin_panel_keyboard())
    await state.clear()


@dp.message(AdminStates.waiting_rating_clear_confirm, F.text == "❌ Yo'q, bekor qilish")
async def rating_clear_cancel(message: Message, state: FSMContext):
    await message.answer("Bekor qilindi.", reply_markup=admin_panel_keyboard())
    await state.clear()


@dp.message(AdminStates.waiting_rating_clear_confirm, F.text == "🔙 Orqaga")
async def rating_clear_back(message: Message, state: FSMContext):
    await go_back(message, state)


# ================= TESTNI TAHRIRLASH =================
@dp.message(F.text == "✏️ Testni tahrirlash")
async def edit_test_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Qaysi sinfdagi testni tahrirlaysiz?",
                         reply_markup=class_selection_keyboard(get_classes()))
    await state.set_state(AdminStates.edit_test_class)


@dp.message(AdminStates.edit_test_class)
async def edit_test_class_select(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await go_back(message, state)
        return
    classes = get_classes()
    for cls in classes:
        if cls['name'] == message.text:
            subjects = get_subjects_by_class(cls['id'])
            if not subjects:
                await message.answer(f"{cls['name']} uchun fanlar yo'q")
                return
            buttons = [[KeyboardButton(text=s['name'])] for s in subjects]
            buttons.append([KeyboardButton(text="🔙 Orqaga")])
            await state.update_data(edit_class_id=cls['id'], edit_class_name=cls['name'])
            await message.answer("Fanni tanlang:",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
            await state.set_state(AdminStates.edit_test_subject)
            return
    await message.answer("Sinf topilmadi")


@dp.message(AdminStates.edit_test_subject)
async def edit_test_subject_select(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await message.answer("Sinfni tanlang:",
                             reply_markup=class_selection_keyboard(get_classes()))
        await state.set_state(AdminStates.edit_test_class)
        return
    data = await state.get_data()
    class_id = data['edit_class_id']
    subjects = get_subjects_by_class(class_id)
    selected = None
    for s in subjects:
        if s['name'] == message.text:
            selected = s
            break
    if not selected:
        await message.answer("Fan topilmadi")
        return
    tests = get_tests_by_subject(selected['id'])
    if not tests:
        await message.answer("Bu fan uchun testlar yo'q")
        return
    buttons = [[KeyboardButton(text=t['name'])] for t in tests]
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    await state.update_data(edit_subject_id=selected['id'])
    await message.answer("Qaysi testni tahrirlaysiz?",
                         reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.set_state(AdminStates.edit_test_select)


@dp.message(AdminStates.edit_test_select)
async def edit_test_select(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        data = await state.get_data()
        subjects = get_subjects_by_class(data['edit_class_id'])
        buttons = [[KeyboardButton(text=s['name'])] for s in subjects]
        buttons.append([KeyboardButton(text="🔙 Orqaga")])
        await message.answer("Fanni tanlang:",
                             reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        await state.set_state(AdminStates.edit_test_subject)
        return
    data = await state.get_data()
    subject_id = data['edit_subject_id']
    tests = get_tests_by_subject(subject_id)
    selected = None
    for t in tests:
        if t['name'] == message.text:
            selected = t
            break
    if not selected:
        await message.answer("Test topilmadi")
        return
    await state.update_data(edit_test_id=selected['id'], edit_test_name=selected['name'])
    await show_edit_question_list(message, state)


async def show_edit_question_list(message: Message, state: FSMContext):
    data = await state.get_data()
    test_id = data['edit_test_id']
    test_name = data['edit_test_name']
    questions = get_questions_by_test(test_id)
    if not questions:
        await message.answer(
            f"'{test_name}' testida savollar yo'q.\n\nYangi savol qo'shish uchun /add_question yuboring.",
            reply_markup=back_keyboard()
        )
        await state.set_state(AdminStates.edit_question_select)
        return
    text = f"📋 '{test_name}' testidagi savollar:\n\n"
    for i, q in enumerate(questions, start=1):
        q_type = "🟢" if q['type'] in ['closed', 'yopiq'] else "🔵"
        short_text = q['question_text'][:60] + "..." if len(q['question_text']) > 60 else q['question_text']
        text += f"{i}. {q_type} [ID: {q['id']}] {short_text}\n"
    text += ("\n━━━━━━━━━━━━━━━━━━━━\n"
             "✏️ Tahrirlash uchun savol raqamini yuboring (masalan: 1)\n"
             "➕ Yangi savol qo'shish uchun: /add_question\n"
             "🗑 Savolni o'chirish uchun: /delete_question <id>\n"
             "🔙 Orqaga: Orqaga tugmasi")
    await message.answer(text, reply_markup=back_keyboard())
    await state.set_state(AdminStates.edit_question_select)


@dp.message(AdminStates.edit_question_select, Command("add_question"))
async def edit_add_question_start(message: Message, state: FSMContext):
    await message.answer("Yangi savol matnini kiriting.\nBekor qilish uchun /cancel yuboring.")
    await state.update_data(new_q={}, new_q_step='text')
    await state.set_state(AdminStates.edit_add_question)


@dp.message(AdminStates.edit_question_select, Command("delete_question"))
async def edit_delete_question(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Format: /delete_question <ID>")
        return
    try:
        q_id = int(args[1])
    except ValueError:
        await message.answer("ID raqam bo'lishi kerak")
        return
    data = await state.get_data()
    test_id = data['edit_test_id']
    questions = get_questions_by_test(test_id)
    if not any(q['id'] == q_id for q in questions):
        await message.answer("Bu ID shu testga tegishli emas")
        return
    delete_question(q_id)
    await message.answer(f"✅ Savol (ID: {q_id}) o'chirildi!")
    await show_edit_question_list(message, state)


@dp.message(AdminStates.edit_question_select, Command("cancel"))
async def edit_cancel(message: Message, state: FSMContext):
    await show_edit_question_list(message, state)


@dp.message(AdminStates.edit_question_select)
async def edit_question_choose(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        data = await state.get_data()
        tests = get_tests_by_subject(data['edit_subject_id'])
        buttons = [[KeyboardButton(text=t['name'])] for t in tests]
        buttons.append([KeyboardButton(text="🔙 Orqaga")])
        await message.answer("Testni tanlang:",
                             reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        await state.set_state(AdminStates.edit_test_select)
        return
    try:
        num = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, savol raqamini kiriting (masalan: 1)")
        return
    data = await state.get_data()
    test_id = data['edit_test_id']
    questions = get_questions_by_test(test_id)
    if num < 1 or num > len(questions):
        await message.answer(f"1 dan {len(questions)} gacha raqam kiriting")
        return
    question = dict(questions[num - 1])
    await state.update_data(edit_question_id=question['id'], edit_question_num=num)
    text = f"📝 Savol #{num} (ID: {question['id']}):\n\n"
    text += f"❓ Matn: {question['question_text']}\n"
    image_status = "✅ bor" if question.get('image_file_id') else "❌ yo'q"
    text += f"🖼 Rasm: {image_status}\n"   # ← YANGI
    text += f"🅰️ A: {question['option_a'] or '(yoq)'}\n"
    text += f"🅱️ B: {question['option_b'] or '(yoq)'}\n"
    text += f"©️ C: {question['option_c'] or '(yoq)'}\n"
    text += f"🅳 D: {question['option_d'] or '(yoq)'}\n"
    text += f"✅ To'g'ri javob: {question['correct_answer']}\n"
    text += f"📋 Turi: {question['type']}\n\nNimani o'zgartirmoqchisiz?"
    await message.answer(text, reply_markup=question_edit_fields_keyboard())
    await state.set_state(AdminStates.edit_question_field)


@dp.message(AdminStates.edit_question_field)
async def edit_question_field(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await show_edit_question_list(message, state)
        return

    field_map = {
        "📝 Savol matni": "question_text",
        "🅰️ A varianti": "option_a",
        "🅱️ B varianti": "option_b",
        "©️ C varianti": "option_c",
        "🅳 D varianti": "option_d",
        "✅ To'g'ri javob": "correct_answer",
        "📋 Savol turi": "type",
        "🖼 Rasm": "image",
    }

    if message.text not in field_map:
        await message.answer("Iltimos, ro'yxatdan tanlang")
        return

    field = field_map[message.text]
    await state.update_data(edit_field=field)

    # RASM uchun alohida oqim
    if field == "image":
        data = await state.get_data()
        q_id = data.get('edit_question_id')
        question = get_question(q_id)
        current_image = question.get('image_file_id') if question else None

        text = "🖼 Rasm bilan amallar:\n\n"
        if current_image:
            text += "✅ Savolda rasm mavjud.\n"
        else:
            text += "❌ Savolda rasm yo'q.\n"
        text += "\nNima qilmoqchisiz?"

        await message.answer(text, reply_markup=image_actions_keyboard())
        await state.set_state(AdminStates.edit_question_image)
        return

    # Boshqa maydonlar uchun
    if field == "type":
        await message.answer("Yangi turni tanlang:", reply_markup=question_type_keyboard())
    else:
        await message.answer(f"Yangi qiymatni kiritish ({message.text}):",
                             reply_markup=back_keyboard())

    await state.set_state(AdminStates.edit_question_value)


@dp.message(AdminStates.edit_question_value)
async def edit_question_value(message: Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await show_edit_question_list(message, state)
        return
    data = await state.get_data()
    q_id = data['edit_question_id']
    field = data['edit_field']
    new_value = message.text.strip()
    if field == "type":
        if new_value == 'yopiq':
            new_value = 'closed'
        elif new_value == 'ochiq':
            new_value = 'open'
        if new_value not in ['closed', 'open']:
            await message.answer("Faqat 'closed' yoki 'open' tanlang")
            return
    try:
        update_question(q_id, **{field: new_value})
        await message.answer(f"✅ O'zgartirildi!")
        questions = get_questions_by_test(data['edit_test_id'])
        question = next((dict(q) for q in questions if q['id'] == q_id), None)
        if not question:
            await show_edit_question_list(message, state)
            return
        text = f"📝 Savol #{data['edit_question_num']} (ID: {question['id']}):\n\n"
        text += f"❓ Matn: {question['question_text']}\n"
        text += f"🅰️ A: {question['option_a'] or '(yoq)'}\n"
        text += f"🅱️ B: {question['option_b'] or '(yoq)'}\n"
        text += f"©️ C: {question['option_c'] or '(yoq)'}\n"
        text += f"🅳 D: {question['option_d'] or '(yoq)'}\n"
        text += f"✅ To'g'ri javob: {question['correct_answer']}\n"
        text += f"📋 Turi: {question['type']}\n\nYana nimani o'zgartirmoqchisiz?"
        await message.answer(text, reply_markup=question_edit_fields_keyboard())
        await state.set_state(AdminStates.edit_question_field)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(AdminStates.edit_add_question)
async def edit_add_question_step(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await message.answer("Bekor qilindi.")
        await show_edit_question_list(message, state)
        return
    data = await state.get_data()
    new_q = data.get('new_q', {})
    step = data.get('new_q_step', 'text')
    if step == 'text':
        new_q['question_text'] = message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='a')
        await message.answer("A variantini kiriting (bo'sh qoldirish uchun '-' yuboring):")
    elif step == 'a':
        new_q['option_a'] = '' if message.text.strip() == '-' else message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='b')
        await message.answer("B variantini kiriting:")
    elif step == 'b':
        new_q['option_b'] = '' if message.text.strip() == '-' else message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='c')
        await message.answer("C variantini kiriting:")
    elif step == 'c':
        new_q['option_c'] = '' if message.text.strip() == '-' else message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='d')
        await message.answer("D variantini kiriting:")
    elif step == 'd':
        new_q['option_d'] = '' if message.text.strip() == '-' else message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='correct')
        await message.answer("To'g'ri javobni kiriting (yopiq uchun A/B/C/D, ochiq uchun matn):")
    elif step == 'correct':
        new_q['correct_answer'] = message.text.strip()
        await state.update_data(new_q=new_q, new_q_step='type')
        await message.answer("Savol turini tanlang:", reply_markup=question_type_keyboard())
    elif step == 'type':
        q_type = message.text.strip().lower()
        if q_type not in ['closed', 'open']:
            await message.answer("Faqat 'closed' yoki 'open'")
            return
        new_q['type'] = q_type
        test_id = data['edit_test_id']
        try:
            add_question(
                test_id=test_id,
                question_text=new_q['question_text'],
                option_a=new_q.get('option_a', ''),
                option_b=new_q.get('option_b', ''),
                option_c=new_q.get('option_c', ''),
                option_d=new_q.get('option_d', ''),
                correct_answer=new_q['correct_answer'],
                q_type=new_q['type']
            )
            await message.answer("✅ Yangi savol qo'shildi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
        await state.update_data(new_q={}, new_q_step=None)
        await show_edit_question_list(message, state)


# ================= SAVOL RASMINI TAHRIRLASH =================

@dp.message(AdminStates.edit_question_image, F.text == "🖼 Yangi rasm yuklash")
async def image_upload_start(message: Message, state: FSMContext):
    await message.answer(
        "Yangi rasmni yuboring (rasm yoki fayl sifatida).\n"
        "Bekor qilish uchun /cancel yuboring.",
        reply_markup=back_keyboard()
    )
    await state.set_state(AdminStates.edit_question_image_upload)


@dp.message(AdminStates.edit_question_image, F.text == "🗑 Rasmni o'chirish")
async def image_remove(message: Message, state: FSMContext):
    data = await state.get_data()
    q_id = data.get('edit_question_id')
    if not q_id:
        await message.answer("Xatolik: savol aniqlanmadi")
        await state.clear()
        return
    try:
        remove_question_image(q_id)
        await message.answer("✅ Rasm o'chirildi!")
        await show_edit_question_list(message, state)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(AdminStates.edit_question_image, F.text == "🔙 Orqaga")
async def image_back(message: Message, state: FSMContext):
    data = await state.get_data()
    q_id = data['edit_question_id']
    test_id = data['edit_test_id']
    questions = get_questions_by_test(test_id)
    question = next((dict(q) for q in questions if q['id'] == q_id), None)
    if not question:
        await show_edit_question_list(message, state)
        return

    text = f"📝 Savol #{data['edit_question_num']} (ID: {question['id']}):\n\n"
    text += f"❓ Matn: {question['question_text']}\n"
    image_status = "✅ bor" if question.get('image_file_id') else "❌ yo'q"
    text += f"🖼 Rasm: {image_status}\n"
    text += f"🅰️ A: {question['option_a'] or '(yoq)'}\n"
    text += f"🅱️ B: {question['option_b'] or '(yoq)'}\n"
    text += f"©️ C: {question['option_c'] or '(yoq)'}\n"
    text += f"🅳 D: {question['option_d'] or '(yoq)'}\n"
    text += f"✅ To'g'ri javob: {question['correct_answer']}\n"
    text += f"📋 Turi: {question['type']}\n\nNimani o'zgartirmoqchisiz?"

    await message.answer(text, reply_markup=question_edit_fields_keyboard())
    await state.set_state(AdminStates.edit_question_field)


@dp.message(AdminStates.edit_question_image_upload, Command("cancel"))
async def image_upload_cancel(message: Message, state: FSMContext):
    await message.answer("Bekor qilindi.")
    await show_edit_question_list(message, state)


@dp.message(AdminStates.edit_question_image_upload, F.photo)
async def image_upload_photo(message: Message, state: FSMContext):
    # Eng katta o'lchamdagi rasmni olamiz
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    q_id = data.get('edit_question_id')

    if not q_id:
        await message.answer("Xatolik: savol aniqlanmadi")
        await state.clear()
        return

    try:
        set_question_image(q_id, file_id)
        await message.answer("✅ Rasm saqlandi!")

        # Savol tafsilotlariga qaytish
        test_id = data['edit_test_id']
        questions = get_questions_by_test(test_id)
        question = next((dict(q) for q in questions if q['id'] == q_id), None)

        text = f"📝 Savol #{data['edit_question_num']} (ID: {question['id']}):\n\n"
        text += f"❓ Matn: {question['question_text']}\n"
        text += f"🖼 Rasm: ✅ bor\n"
        text += f"🅰️ A: {question['option_a'] or '(yoq)'}\n"
        text += f"🅱️ B: {question['option_b'] or '(yoq)'}\n"
        text += f"©️ C: {question['option_c'] or '(yoq)'}\n"
        text += f"🅳 D: {question['option_d'] or '(yoq)'}\n"
        text += f"✅ To'g'ri javob: {question['correct_answer']}\n"
        text += f"📋 Turi: {question['type']}\n\nYana nimani o'zgartirmoqchisiz?"

        await message.answer(text, reply_markup=question_edit_fields_keyboard())
        await state.set_state(AdminStates.edit_question_field)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(AdminStates.edit_question_image_upload, F.document)
async def image_upload_document(message: Message, state: FSMContext):
    # Faqat rasm fayllarini qabul qilamiz
    if not message.document.mime_type or not message.document.mime_type.startswith("image/"):
        await message.answer("Iltimos, faqat rasm fayl yuboring!")
        return

    file_id = message.document.file_id
    data = await state.get_data()
    q_id = data.get('edit_question_id')

    if not q_id:
        await message.answer("Xatolik: savol aniqlanmadi")
        await state.clear()
        return

    try:
        set_question_image(q_id, file_id)
        await message.answer("✅ Rasm saqlandi!")
        await show_edit_question_list(message, state)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(AdminStates.edit_question_image_upload)
async def image_upload_invalid(message: Message, state: FSMContext):
    await message.answer("Iltimos, rasm yuboring yoki /cancel bosing.")


# ================= ISHGA TUSHIRISH =================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(
        bot,
        polling_timeout=30,        # 30 soniya kutish
        request_timeout=60,        # So'rov uchun 60 soniya
        relax=0.5,                 # So'rovlar orasida 0.5s pauza
    )


if __name__ == "__main__":
    asyncio.run(main())
