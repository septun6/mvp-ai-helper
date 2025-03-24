CREATE TABLE vacation_planning (
    id SERIAL PRIMARY KEY,                          -- Унікальний ідентифікатор
    name VARCHAR(255) NOT NULL,                     -- Ім'я користувача
    group_size INT NOT NULL,                        -- Кількість людей у групі
    start_date DATE NOT NULL,                       -- Дата початку
    end_date DATE NOT NULL,                         -- Дата закінчення
    vacation_type TEXT[] NOT NULL,                  -- Тип відпочинку (масив текстів)
    climate_preference VARCHAR(50) NOT NULL,        -- Кліматичні уподобання
    goals TEXT NOT NULL,                            -- Цілі відпустки
    activities TEXT[] NOT NULL,                     -- Заплановані активності (масив текстів)
    budget_range INT NOT NULL,                      -- Бюджет
    special_needs TEXT,                             -- Особливі потреби
    additional_info TEXT,                           -- Додаткова інформація
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Дата створення запису
);
