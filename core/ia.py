import os
from dotenv import load_dotenv
import google.generativeai as genai

# Cargar variables de entorno
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La clave de API GEMINI_API_KEY no está configurada.")

genai.configure(api_key=api_key) # pyright: ignore[reportPrivateImportUsage]

# Modelo de IA a utilizar
MODEL = "models/gemini-2.0-flash"

# ===== PROMPTS PERSONALIZADOS =====

PROMPTS = {
    "Requisitos": lambda texto: (
        "A partir de las siguientes historias de usuario:\n\n"
        f"{texto}\n\n"
        "Genera una lista de requisitos funcionales. Para cada requisito:\n"
        "1. Debe empezar con RF seguido de un número secuencial (RF1, RF2, etc.)\n"
        "2. Debe indicar a qué historia de usuario corresponde usando [HU#]\n"
        "3. Debe ser atómico (una sola funcionalidad)\n"
        "4. Debe ser medible y verificable\n"
        "5. Debe estar redactado en tercera persona del presente\n"
        "5. Debe ser redacto asi: El sistema debe ....\n"
        "Ejemplo del formato esperado:\n"
        "RF1 [HU1] El sistema debe permitir el inicio de sesión mediante correo y contraseña\n"
        "RF2 [HU1] El sistema debe validar las credenciales contra la base de datos\n"
        "RF3 [HU2] El sistema debe mostrar el listado de productos disponibles\n"
        "Devuelve solo la lista de requisitos siguiendo este formato, sin explicaciones ni títulos adicionales."
    ),

    "Historia de Usuario": lambda nombre_proyecto, descripcion: (
        f"Dame historias de usuario enumeradas con HU y el número secuencial para un proyecto de software llamado '{nombre_proyecto}' y con la siguiente descripción '{descripcion}'. "
        "Con la estructura: Como, Quiero, Para. No le des formato a la respuesta. Ni uses lenguaje técnico si no que sea como un usuario común."
    ),

    "Diagrama de flujo": lambda texto: (
        "Genera un diagrama de flujo único en sintaxis Mermaid (Markdown) que cumpla con:\n"
        "1. Incluir TODOS los usuarios/actores en el mismo flujo\n"
        "2. Usar estructura flowchart TD con nodos concisos (máximo 3 palabras)\n"
        "3. Decisiones con formato: {¿Pregunta?} y flechas -->|sí|/-->|no|\n"
        "4. Un solo nodo inicial [Inicio] y final [Fin]\n"
        "5. Conexiones lógicas sin bucles infinitos\n\n"
        "Instrucciones técnicas:\n"
        "- Usar IDs únicos en inglés para nodos (Ej: A, B, C1)\n"
        "- Evitar caracteres especiales en IDs\n"
        "- Alinear con espacios: '  ' para indentación\n"
        "- Validar sintaxis en Mermaid Live Editor\n\n"
        f"Historias de usuario:\n{texto}\n\n"
        "Formato de salida (solo código, sin explicaciones):\n"
        "flowchart TD\n"
        "  A[Inicio] --> B[Acción 1]\n"
        "  B --> C{¿Decisión?}\n"
        "  C -->|sí| D[Acción 2]\n"
        "  C -->|no| E[Acción 3]\n"
        "  D --> F[Fin]\n"
        "  E --> F"
    ),

    "Diagrama de clases": lambda historias_usuario, requisitos: (
        "Genera un diagrama de clases en sintaxis Mermaid basado en las siguientes historias de usuario y requisitos funcionales:\n\n"
        f"Historias de Usuario:\n{historias_usuario}\n\n"
        f"Requisitos Funcionales:\n{requisitos}\n\n"
        "Incluye las siguientes características:\n"
        "- Extrae las clases principales identificadas en las historias de usuario y requisitos.\n"
        "- Para cada requisito funcional, identifica los métodos necesarios en las clases correspondientes.\n"
        "- Define atributos con tipo y visibilidad (+ público, - privado, # protegido) basados en la información de los requisitos.\n"
        "- Establece las relaciones entre clases: herencia (<|--), asociación (--), composición (*--), agregación (o--).\n"
        "- Incluye multiplicidades cuando correspondan.\n"
        "- Asegura que cada clase tenga los métodos necesarios para cumplir con los requisitos funcionales.\n"
        "-no utilices explicaciones del diagrama.\n"
        "classDiagram\n"
        "    class Usuario {\n"
        "        +nombre: String\n"
        "        +login()\n"
        "    }\n"
        "    class Cliente {\n"
        "        +id: Int\n"
        "        +realizarCompra()\n"
        "    }\n"
        "    Usuario <|-- Cliente\n"
        "    Cliente *-- Pedido : realiza\n"
        "    Pedido o-- Producto : contiene"
    ),

    "Diagrama de Entidad-Relacion": lambda historias_usuario, requisitos: (
        "Genera un diagrama entidad-relación (ER) en sintaxis Mermaid basado en las siguientes historias de usuario y requisitos funcionales:\n\n"
        f"Historias de Usuario:\n{historias_usuario}\n\n"
        f"Requisitos Funcionales:\n{requisitos}\n\n"
        "Indicaciones claras para la generación:\n"
        "- Analiza las historias de usuario y requisitos para identificar las entidades principales y sus relaciones.\n"
        "- Cada requisito funcional debe estar reflejado en las entidades y sus atributos.\n"
        "- Usa la palabra clave erDiagram para iniciar el diagrama.\n"
        "- Define entidades con atributos dentro de llaves {}, indicando tipo y clave primaria (PK) si aplica.\n"
        "- Identifica las relaciones necesarias para cumplir los requisitos funcionales.\n"
        "- Usa cardinalidades con los símbolos ||, |o, }o, }| según notación crow's foot.\n"
        "- Define relaciones con la sintaxis: ENTIDAD1 <cardinalidad>--<cardinalidad> ENTIDAD2 : descripción\n"
        "- Usa direccion TB o LR.\n"
        "- Usa nombres de entidades en mayúsculas y sin espacios ni caracteres especiales.\n"
        "- Asegura que cada entidad tenga los atributos necesarios para cumplir los requisitos.\n"
        "- Devuelve solo el bloque de código completo en Mermaid, sin explicaciones ni texto adicional.\n\n"
        "Ejemplo:\n"
        "erDiagram\n"
        "    CLIENTE {\n"
        "        int id PK\n"
        "        string nombre\n"
        "    }\n"
        "    PEDIDO {\n"
        "        int id PK\n"
        "        date fecha\n"
        "    }\n"
        "    CLIENTE ||--o{ PEDIDO : realiza\n"
        "    PEDIDO }o--|| PRODUCTO : contiene"
    ),

    "Diagrama de secuencia": lambda texto: (
        "Genera un diagrama de secuencia en sintaxis Mermaid basado en el siguiente texto:\n\n"
        f"{texto}\n\n"
        "Incluye actores, objetos, mensajes y retornos.\n"
        "-no utilices explicaciones del diagrama.\n"
        "Ejemplo:\n"
        "sequenceDiagram\n"
        "    participant Usuario\n"
        "    participant Sistema\n"
        "    Usuario->>Sistema: Solicita iniciar sesión\n"
        "    Sistema-->>Usuario: Muestra pantalla principal"
    ),

    "Diagrama de estado": lambda texto: (
        "Genera un diagrama de estados en sintaxis Mermaid basado en el siguiente texto:\n\n"
        "-no utilices explicaciones del diagrama.\n"
        f"{texto}\n\n"
        "Ejemplo:\n"
        "stateDiagram-v2\n"
        "    [*] --> Estado1\n"
        "    Estado1 --> Estado2: eventoA\n"
        "    Estado2 --> Estado3: eventoB\n"
        "    Estado3 --> [*]"
    ),

    "Diagrama de C4-contexto": lambda texto: (
        "Genera un diagrama C4 de tipo contexto (c4Context) en sintaxis Mermaid basado en la siguiente descripción del sistema:\n\n"
        f"{texto}\n\n"
        "Sigue cuidadosamente estas indicaciones para la sintaxis del diagrama Mermaid:\n\n"
        "- Se empieza con C4Context para definir el tipo de diagrama.\n\n"
        "Estructura y elementos obligatorios:\n"
        "- Usa Person(alias, nombre, descripción) para representar actores humanos internos.\n"
        "- Usa Person_Ext(alias, nombre, descripción) para representar actores externos.\n"
        "- Usa System(alias, nombre, descripción) para representar el sistema principal.\n"
        "- Usa System_Ext(alias, nombre, descripción) para sistemas externos conectados."
        "- Usa SystemDb(alias, nombre, descripción) para bases de datos internas del sistema."
        "- Usa SystemDb_Ext(alias, nombre, descripción) para bases de datos externas."
        "- Usa SystemQueue o SystemQueue_Ext si el sistema involucra colas de mensajes."

        "- Agrupa sistemas internos usando Enterprise_Boundary(alias, nombre).\n"
        "- Puedes anidar límites usando System_Boundary y Boundary si es necesario.\n\n"
        "Relaciones:\n"
        "- Usa Rel(origen, destino, etiqueta) para relaciones unidireccionales.\n"
        "- Usa BiRel(origen, destino, etiqueta) para relaciones bidireccionales.\n"
        "- Puedes añadir un protocolo como cuarto parámetro en Rel (ej. 'SMTP').\n\n"
        "Estilos personalizados (opcionales pero recomendados para enriquecer el diagrama):\n"
        "- Usa UpdateElementStyle(alias, $fontColor=, $bgColor=, $borderColor=) para personalizar elementos.\n"
        "- Usa UpdateRelStyle(from, to, $textColor=, $lineColor=) para personalizar relaciones.\n"
        "Devuelve únicamente el código Mermaid completo y válido, sin usar la palabra 'mermaid' ni comillas ni backticks. El código debe comenzar directamente con las líneas %%{ init ... }%%.\n\n"
        "Ojo, tiene que empezar si o si con la siguiente linea: C4Context"
        "Ejemplo:\n"
        "C4Context\n"
        "    title \"System Context diagram for Internet Banking System\"\n"
        "    Enterprise_Boundary(b0, \"BankBoundary0\") {\n"
        "        Person(customerA, \"Banking Customer A\", \"A customer of the bank, with personal bank accounts.\")\n"
        "        Person(customerB, \"Banking Customer B\")\n"
        "        Person_Ext(customerC, \"Banking Customer C\", \"desc\")\n"
        "        Person(customerD, \"Banking Customer D\", \"A customer of the bank, <br/> with personal bank accounts.\")\n"
        "        System(SystemAA, \"Internet Banking System\", \"Allows customers to view information about their bank accounts, and make payments.\")\n"
        "\n"
        "        Enterprise_Boundary(b1, \"BankBoundary\") {\n"
        "            SystemDb_Ext(SystemE, \"Mainframe Banking System\", \"Stores all of the core banking information about customers, accounts, transactions, etc.\")\n"
        "\n"
        "            System_Boundary(b2, \"BankBoundary2\") {\n"
        "                System(SystemA, \"Banking System A\")\n"
        "                System(SystemB, \"Banking System B\", \"A system of the bank, with personal bank accounts. next line.\")\n"
        "            }\n"
        "\n"
        "            System_Ext(SystemC, \"E-mail system\", \"The internal Microsoft Exchange e-mail system.\")\n"
        "            SystemDb(SystemD, \"Banking System D Database\", \"A system of the bank, with personal bank accounts.\")\n"
        "\n"
        "            Boundary(b3, \"BankBoundary3\", \"boundary\") {\n"
        "                SystemQueue(SystemF, \"Banking System F Queue\", \"A system of the bank.\")\n"
        "                SystemQueue_Ext(SystemG, \"Banking System G Queue\", \"A system of the bank, with personal bank accounts.\")\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "\n"
        "    BiRel(customerA, SystemAA, \"Uses\")\n"
        "    BiRel(SystemAA, SystemE, \"Uses\")\n"
        "    Rel(SystemAA, SystemC, \"Sends e-mails\", \"SMTP\")\n"
        "    Rel(SystemC, customerA, \"Sends e-mails to\")\n"
        "\n"
        "    UpdateElementStyle(customerA, $fontColor=\"red\", $bgColor=\"grey\", $borderColor=\"red\")\n"
        "    UpdateRelStyle(customerA, SystemAA, $textColor=\"blue\", $lineColor=\"blue\", $offsetX=\"5\")\n"
        "    UpdateRelStyle(SystemAA, SystemE, $textColor=\"blue\", $lineColor=\"blue\", $offsetY=\"-10\")\n"
        "    UpdateRelStyle(SystemAA, SystemC, $textColor=\"blue\", $lineColor=\"blue\", $offsetY=\"-40\", $offsetX=\"-50\")\n"
        "    UpdateRelStyle(SystemC, customerA, $textColor=\"red\", $lineColor=\"red\", $offsetX=\"-50\", $offsetY=\"20\")\n"
        "\n"
        "    UpdateLayoutConfig($c4ShapeInRow=\"3\", $c4BoundaryInRow=\"1\")"
    ),
    
    "Diagrama de C4-contenedor": lambda texto: (
        "Genera un diagrama C4 de tipo contenedor (C4Container) en sintaxis Mermaid basado en la siguiente descripción del sistema:\n\n"
        f"{texto}\n\n"
        "Sigue cuidadosamente estas indicaciones para la sintaxis del diagrama Mermaid:\n\n"
        "- Se empieza con C4Container para definir el tipo de diagrama.\n\n"
        "- Trata de sea en español las especificaciones y descripciones"
        "- Los diagramas deben tener un orden entendible"
        "Estructura y elementos obligatorios:\n"
        "- Usa Container(alias, nombre, tecnología, descripción) para representar contenedores principales.\n"
        "- Usa ContainerDb(alias, nombre, tecnología, descripción) para bases de datos internas.\n"
        "- Usa ContainerQueue(alias, nombre, tecnología, descripción) para colas internas.\n"
        "- Usa Container_Ext(alias, nombre, tecnología, descripción) para contenedores externos.\n"
        "- Usa ContainerDb_Ext(alias, nombre, tecnología, descripción) y ContainerQueue_Ext(alias, nombre, tecnología, descripción) para bases de datos y colas externas.\n"
        "- Usa Container_Boundary(alias, nombre) para agrupar contenedores del sistema.\n\n"

        "Otros elementos permitidos:\n"
        "- Usa Person(alias, nombre, descripción) para actores internos.\n"
        "- Usa Person_Ext(alias, nombre, descripción) para actores externos.\n"
        "- Usa System_Ext(alias, nombre, descripción) para sistemas externos.\n\n"

        "Relaciones:\n"
        "- Usa Rel(origen, destino, etiqueta, protocolo) para relaciones unidireccionales.\n"
        "- Usa BiRel(origen, destino, etiqueta, protocolo) para relaciones bidireccionales.\n"
        "- Usa Rel_Back(origen, destino, etiqueta, protocolo) para relaciones desde bases de datos u otros componentes al contenedor.\n\n"

        "Estilos personalizados (opcionales pero recomendados):\n"
        "- Usa UpdateElementStyle(alias, $fontColor=\"\", $bgColor=\"\", $borderColor=\"\") para personalizar elementos.\n"
        "- Usa UpdateRelStyle(origen, destino, $textColor=\"\", $lineColor=\"\", $offsetX=\"\", $offsetY=\"\") para personalizar relaciones.\n"
        "- Usa UpdateLayoutConfig($c4ShapeInRow=\"\", $c4BoundaryInRow=\"\") para modificar la distribución del diagrama.\n\n"

        "Devuelve únicamente el código Mermaid completo y válido, sin usar la palabra 'mermaid', sin comillas ni backticks. El código debe comenzar directamente con las líneas C4Container.\n\n"
        "Te doy un ejemplo de como podria ser la estructura:\n"
        "C4Container\n"
        "    title \"Container diagram for Internet Banking System\"\n"
        "\n"
        "    System_Ext(email_system, \"E-Mail System\", \"The internal Microsoft Exchange system\", $tags=\"v1.0\")\n"
        "    Person(customer, \"Customer\", \"A customer of the bank, with personal bank accounts\", $tags=\"v1.0\")\n"
        "\n"
        "    Container_Boundary(c1, \"Internet Banking\") {\n"
        "        Container(spa, \"Single-Page App\", \"JavaScript, Angular\", \"Provides all the Internet banking functionality to customers via their web browser\")\n"
        "        Container_Ext(mobile_app, \"Mobile App\", \"C#, Xamarin\", \"Provides a limited subset of the Internet banking functionality to customers via their mobile device\")\n"
        "        Container(web_app, \"Web Application\", \"Java, Spring MVC\", \"Delivers the static content and the Internet banking SPA\")\n"
        "        ContainerDb(database, \"Database\", \"SQL Database\", \"Stores user registration information, hashed auth credentials, access logs, etc.\")\n"
        "        ContainerDb_Ext(backend_api, \"API Application\", \"Java, Docker Container\", \"Provides Internet banking functionality via API\")\n"
        "    }\n"
        "\n"
        "    System_Ext(banking_system, \"Mainframe Banking System\", \"Stores all of the core banking information about customers, accounts, transactions, etc.\")\n"
        "\n"
        "    Rel(customer, web_app, \"Uses\", \"HTTPS\")\n"
        "    UpdateRelStyle(customer, web_app, $offsetY=\"60\", $offsetX=\"90\")\n"
        "    Rel(customer, spa, \"Uses\", \"HTTPS\")\n"
        "    UpdateRelStyle(customer, spa, $offsetY=\"-40\")\n"
        "    Rel(customer, mobile_app, \"Uses\")\n"
        "    UpdateRelStyle(customer, mobile_app, $offsetY=\"-30\")\n"
        "\n"
        "    Rel(web_app, spa, \"Delivers\")\n"
        "    UpdateRelStyle(web_app, spa, $offsetX=\"130\")\n"
        "    Rel(spa, backend_api, \"Uses\", \"async, JSON/HTTPS\")\n"
        "    Rel(mobile_app, backend_api, \"Uses\", \"async, JSON/HTTPS\")\n"
        "    Rel_Back(database, backend_api, \"Reads from and writes to\", \"sync, JDBC\")\n"
        "\n"
        "    Rel(email_system, customer, \"Sends e-mails to\")\n"
        "    UpdateRelStyle(email_system, customer, $offsetX=\"-45\")\n"
        "    Rel(backend_api, email_system, \"Sends e-mails using\", \"sync, SMTP\")\n"
        "    UpdateRelStyle(backend_api, email_system, $offsetY=\"-60\")\n"
        "    Rel(backend_api, banking_system, \"Uses\", \"sync/async, XML/HTTPS\")\n"
        "    UpdateRelStyle(backend_api, banking_system, $offsetY=\"-50\", $offsetX=\"-140\")"
    ),

    "Diagrama de C4-implementación": lambda texto: (
        "Genera un diagrama C4 de tipo implementación (C4Deployment) en sintaxis Mermaid basado en la siguiente descripción del sistema:\n\n"
        f"{texto}\n\n"
        "Sigue cuidadosamente estas indicaciones para la sintaxis del diagrama Mermaid:\n\n"
        "- Comienza el código con:\n"
        "  C4Deployment\n\n"
        "- Trata de sea en español las especificaciones y descripciones"
        "- Los diagramas deben tener un orden entendible"
        "Estructura y elementos obligatorios:\n"
        "- Usa Deployment_Node(alias, nombre, tipo, descripción) para representar nodos físicos o virtuales.\n"
        "- También puedes usar:\n"
        "  - Node(): versión corta de Deployment_Node()\n"
        "  - Node_L(): alineado a la izquierda\n"
        "  - Node_R(): alineado a la derecha\n"
        "- Dentro de los nodos se colocan:\n"
        "  - Container(alias, nombre, tecnología, descripción) para aplicaciones.\n"
        "  - ContainerDb(alias, nombre, tecnología, descripción) para bases de datos.\n"

        "Relaciones:\n"
        "- Usa Rel(origen, destino, descripción, protocolo) para relaciones unidireccionales.\n"
        "- Usa Rel_U(), Rel_D(), Rel_L(), Rel_R() si quieres controlar la dirección de la flecha.\n"

        "Estilos personalizados:\n"
        "- Usa UpdateRelStyle(origen, destino, $textColor=\"\", $lineColor=\"\", $offsetX=\"\", $offsetY=\"\") para personalizar relaciones.\n"
        "- Usa UpdateLayoutConfig($c4ShapeInRow=\"\", $c4BoundaryInRow=\"\") para controlar la distribución visual.\n\n"

        "Devuelve solo el código Mermaid. No uses la palabra 'mermaid', comillas ni backticks.\n\n"

        "Ejemplo:\n"

        "C4Deployment\n"
        "    title Deployment Diagram for Internet Banking System - Live\n\n"
        "    Deployment_Node(mob, \"Customer's mobile device\", \"Apple IOS or Android\") {\n"
        "        Container(mobile, \"Mobile App\", \"Xamarin\", \"Provides a limited subset of the Internet Banking functionality to customers via their mobile device.\")\n"
        "    }\n\n"
        "    Deployment_Node(comp, \"Customer's computer\", \"Microsoft Windows or Apple macOS\") {\n"
        "        Deployment_Node(browser, \"Web Browser\", \"Google Chrome, Mozilla Firefox,<br/> Apple Safari or Microsoft Edge\") {\n"
        "            Container(spa, \"Single Page Application\", \"JavaScript and Angular\", \"Provides all of the Internet Banking functionality to customers via their web browser.\")\n"
        "        }\n"
        "    }\n\n"
        "    Deployment_Node(plc, \"Big Bank plc\", \"Big Bank plc data center\") {\n"
        "        Deployment_Node(dn, \"bigbank-api*** x8\", \"Ubuntu 16.04 LTS\") {\n"
        "            Deployment_Node(apache, \"Apache Tomcat\", \"Apache Tomcat 8.x\") {\n"
        "                Container(api, \"API Application\", \"Java and Spring MVC\", \"Provides Internet Banking functionality via a JSON/HTTPS API.\")\n"
        "            }\n"
        "        }\n"
        "        Deployment_Node(bb2, \"bigbank-web*** x4\", \"Ubuntu 16.04 LTS\") {\n"
        "            Deployment_Node(apache2, \"Apache Tomcat\", \"Apache Tomcat 8.x\") {\n"
        "                Container(web, \"Web Application\", \"Java and Spring MVC\", \"Delivers the static content and the Internet Banking single page application.\")\n"
        "            }\n"
        "        }\n"
        "        Deployment_Node(bigbankdb01, \"bigbank-db01\", \"Ubuntu 16.04 LTS\") {\n"
        "            Deployment_Node(oracle, \"Oracle - Primary\", \"Oracle 12c\") {\n"
        "                ContainerDb(db, \"Database\", \"Relational Database Schema\", \"Stores user registration information, hashed authentication credentials, access logs, etc.\")\n"
        "            }\n"
        "        }\n"
        "        Deployment_Node(bigbankdb02, \"bigbank-db02\", \"Ubuntu 16.04 LTS\") {\n"
        "            Deployment_Node(oracle2, \"Oracle - Secondary\", \"Oracle 12c\") {\n"
        "                ContainerDb(db2, \"Database\", \"Relational Database Schema\", \"Stores user registration information, hashed authentication credentials, access logs, etc.\")\n"
        "            }\n"
        "        }\n"
        "    }\n\n"
        "    Rel(mobile, api, \"Makes API calls to\", \"json/HTTPS\")\n"
        "    Rel(spa, api, \"Makes API calls to\", \"json/HTTPS\")\n"
        "    Rel_U(web, spa, \"Delivers to the customer's web browser\")\n"
        "    Rel(api, db, \"Reads from and writes to\", \"JDBC\")\n"
        "    Rel(api, db2, \"Reads from and writes to\", \"JDBC\")\n"
        "    Rel_R(db, db2, \"Replicates data to\")\n\n"
        "    UpdateRelStyle(spa, api, $offsetY=\"-40\")\n"
        "    UpdateRelStyle(web, spa, $offsetY=\"-40\")\n"
        "    UpdateRelStyle(api, db, $offsetY=\"-20\", $offsetX=\"5\")\n"
        "    UpdateRelStyle(api, db2, $offsetX=\"-40\", $offsetY=\"-20\")\n"
        "    UpdateRelStyle(db, db2, $offsetY=\"-10\")"
    ),


    "caja negra": lambda nombre_proyecto, descripcion: (
        "Genera casos de prueba de caja negra detallados basados en el siguiente texto o historias de usuario:\n\n"
        f"{nombre_proyecto, descripcion}\n\n"
        "Para cada caso de prueba, estructura la información de la siguiente forma sin ningún formato enriquecido" 
        "(sin negritas, sin cursivas, sin listas con viñetas, solo texto plano):\n"
        "- Identificador: con formato PCN-01, PCN-02, PCN-03, ...\n"
        "- Nombre de la prueba de caja negra\n"
        "- Propósito\n"
        "- Prerrequisito\n"
        "- Datos de entrada\n"
        "- Pasos para realizar la prueba\n"
        "- Resultado esperado\n"
        "Devuelve sólo el texto claro y estructurado siguiendo este formato para cada caso de prueba, sin numeraciones o texto adicional fuera de la estructura."
    ),

    "smoke": lambda nombre_proyecto, descripcion: (
        "Genera pruebas smoke (pruebas rápidas y mínimas) para validar la funcionalidad esencial según el siguiente texto:\n\n"
        f"Proyecto: {nombre_proyecto}\nDescripción: {descripcion}\n\n"
        "Devuelve sólo texto claro y estructurado con el siguiente formato para cada prueba:\n"
        "- Nombre de la prueba\n"
        "- Propósito\n"
        "- Pasos mínimos\n"
        "- Resultado esperado\n\n"
        "No incluyas numeraciones ni texto adicional fuera de esta estructura."
    ),

}

# ===== FUNCIONES DE GENERACIÓN =====

def _generar_contenido(prompt: str) -> str:
    try:
        model = genai.GenerativeModel(MODEL) # pyright: ignore[reportPrivateImportUsage]
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[ERROR] No se pudo generar contenido: {e}"

def generar_subartefacto_con_prompt(tipo: str, **kwargs) -> str:
    if tipo not in PROMPTS:
        raise ValueError (f"[ERROR] Tipo de artefacto desconocido: {tipo}")

    prompt_func = PROMPTS[tipo]
    prompt = prompt_func(**kwargs)
    return _generar_contenido(prompt)

#=====  codigo de extrae reqquisitos de la HU=======
def extraer_requisitos(historia_texto: str) -> str:
    prompt = (
        "Eres un ingeniero de software especializado en análisis de requisitos.\n"
        "Dada la siguiente lista de historias de usuario, cada una identificada con HU y su número secuencial:\n"
        f"{historia_texto}\n"
        "Extrae exactamente los requisitos funcionales clave para cada historia de usuario. "
        "Enumera cada requisito como RF (Requisito Funcional) seguido del número secuencial correspondiente (por ejemplo, RF1, RF2, etc.).\n"
        "Cada requisito debe ser claro, específico y estar redactado en tercera persona.\n"
        "Devuelve únicamente la lista de requisitos, uno por línea, sin títulos, numeración adicional ni explicaciones."
    )
    return _generar_contenido(prompt)

