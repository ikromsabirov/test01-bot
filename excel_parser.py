import openpyxl
from database import add_question

def parse_excel(file_path, test_id):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    
    # Birinchi qator sarlavha bo'lishi kerak
    headers = [cell.value for cell in sheet[1]]
    
    # Majburiy ustunlar
    required = ['Savol', 'Variant A', 'Variant B', 'Variant C', 'Variant D', 'To\'g\'ri javob']
    for col in required:
        if col not in headers:
            raise ValueError(f"Excel faylida '{col}' ustuni topilmadi")
    
    # Ustun indekslarini aniqlash
    idx_question = headers.index('Savol')
    idx_a = headers.index('Variant A')
    idx_b = headers.index('Variant B')
    idx_c = headers.index('Variant C')
    idx_d = headers.index('Variant D')
    idx_correct = headers.index('To\'g\'ri javob')
    
    # Turi ustuni ixtiyoriy, agar yo'q bo'lsa variantlardan aniqlanadi
    idx_type = None
    if 'Turi' in headers:
        idx_type = headers.index('Turi')
    
    question_count = 0
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[idx_question] is None:
            continue
        question_text = str(row[idx_question]).strip()
        option_a = str(row[idx_a]).strip() if row[idx_a] else ""
        option_b = str(row[idx_b]).strip() if row[idx_b] else ""
        option_c = str(row[idx_c]).strip() if row[idx_c] else ""
        option_d = str(row[idx_d]).strip() if row[idx_d] else ""
        correct = str(row[idx_correct]).strip()
        
        # Savol turini aniqlash
        if idx_type is not None and row[idx_type] is not None:
            q_type = str(row[idx_type]).strip().lower()
        else:
            # Agar barcha variantlar bo'sh bo'lsa - ochiq, aks holda yopiq
            if option_a == "" and option_b == "" and option_c == "" and option_d == "":
                q_type = "open"
            else:
                q_type = "closed"
        
        # To'g'ri javobni moslashtirish
        if q_type == "closed":
            # Yopiq savol uchun javob A/B/C/D bo'lishi kerak
            if correct.upper() not in ['A', 'B', 'C', 'D']:
                # Agar javob matn bo'lsa, variantlardan qidirish
                if correct == option_a:
                    correct = "A"
                elif correct == option_b:
                    correct = "B"
                elif correct == option_c:
                    correct = "C"
                elif correct == option_d:
                    correct = "D"
                else:
                    # Noto'g'ri javob, uni ochiq deb hisoblaymiz
                    q_type = "open"
        
        add_question(test_id, question_text, option_a, option_b, option_c, option_d, correct, q_type)
        question_count += 1
    
    return question_count