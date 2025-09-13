codigo para crear el entorno virtual 

virtualenv -p python3 env

codigo para crear el archivo del requirements.txt

pip freeze > requirements.txt

codigo para instalar los paquetes de que tiene requirements.txt

pip install -r .\requirements.txt

codigo para activar el entorno virtual

.\env\Scripts\Activate

codigo para desactivar el entorno virtual

deactivate

codigo para ejecutar 

python manage.py runserver
