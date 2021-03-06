### Task
Нам необхідно проаналізувати ситуацію із доступністю шкіл у Подільскому районі. Для цього пропонуємо:
1. Розпарсити HTML із адресами будинків Подільского району та прив’язками до шкіл. http://bit.ly/2VCC2vo
2. Закодувати координати кожного будинку через Google API
3. Скопіювати (бажано зпарсити) адреси шкіл з сайту http://ua.kiev.parentsportal.com.ua/schools/?rayon=146 або іншого відкритого джерела.
4. Визначити будинки відстань від кожного будинку до своєї школи по повітряній лініїї. Для розрахунку відстані між точками вам знадобиться одна з наведених вище бібліотек.
5. Експортувати базу даних з будинками (та відстанями до шкіл як одна з характеристик будинку) у шейп-файл.
6. Відкрити шейп-файл в QGIS та виділити червоним кольором будинки, які знаходяться від школи на відстані більшій за 800м по повітряній лінії.
7. Розрахувати (кодом, бажано в Pandas) розподіл будинків за віддаленістю до своїх шкіл (%% будинків, що віддалені більше ніж на 1000 м, 800 м, 500 м, мнеше ніж 500 м). 
8. Розрахувати медіанне значення віддаленості будинків від шкіл для всього району.
### Usage
1. install QGIS
2. install modules from requirements.txt
3. set up HERE_MAPS_APP_ID, HERE_MAPS_APP_CODE env variables for here maps api. How to obtain https://developer.here.com
4. run script
### Known issues
1. несколько школ имеют одинаковый номер, например школа номер 19 (школа интернат и межигорская гимназия)
в данном решении выбирается школа интернат (неверно)
2. некоторые адреса явно не из подольского района (на троещине или красном хуторе), нужно проверить в дальнейшем.
### text results
distance_bucket

less 500        0.389831

500-800         0.205650

800-1000        0.056497

greater 1000    0.348023

home to school median distance: 624.0