<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Comentarios Vulnerable - Lab</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: #333;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { margin-bottom: 10px; }
        .warning {
            background: #ff4444;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
        }
        .content { padding: 30px; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea { min-height: 100px; resize: vertical; }
        button {
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background: #5568d3; }
        .comments {
            margin-top: 40px;
            border-top: 2px solid #eee;
            padding-top: 30px;
        }
        .comment {
            background: #f9f9f9;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .comment-author {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .comment-date {
            font-size: 12px;
            color: #999;
            margin-bottom: 10px;
        }
        .comment-text {
            color: #333;
            line-height: 1.6;
        }
        .vuln-info {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .vuln-info h3 {
            color: #856404;
            margin-bottom: 10px;
        }
        .vuln-info ul {
            margin-left: 20px;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔓 Sistema de Comentarios Vulnerable</h1>
            <p>Aplicación PHP para Laboratorio de Seguridad</p>
        </div>
        
        <div class="warning">
            ⚠️ SOLO PARA LABORATORIO - CONTIENE VULNERABILIDADES INTENCIONALES
        </div>
        <?php echo "\n"; ?>
        <div class="content">

            <div class="vuln-info">
                <h3>🐛 Vulnerabilidades Implementadas:</h3>
                <ul>
                    <li><strong>XSS Reflejado:</strong> El campo de búsqueda no sanitiza la entrada</li>
                    <li><strong>XSS Almacenado:</strong> Los comentarios se guardan sin filtrar</li>
                    <li><strong>SQL Injection:</strong> La búsqueda es vulnerable a inyección SQL</li>
                    <li><strong>Sin validación:</strong> No hay protección CSRF ni validación de entrada</li>
                </ul>
            </div>

            <h2>Agregar Comentario</h2>
            <form method="POST" action="">
                <div class="form-group">
                    <label for="nombre">Nombre:</label>
                    <input type="text" id="nombre" name="nombre" required>
                </div>
                <div class="form-group">
                    <label for="comentario">Comentario:</label>
                    <textarea id="comentario" name="comentario" required></textarea>
                </div>
                <button type="submit" name="agregar">Publicar Comentario</button>
            </form>

            <h2 style="margin-top: 40px;">Buscar Comentarios</h2>
            <form method="GET" action="">
                <div class="form-group">
                    <label for="buscar">Buscar por nombre:</label>
                    <input type="text" id="buscar" name="buscar" 
                           value="<?php echo isset($_GET['buscar']) ? $_GET['buscar'] : ''; ?>">
                </div>
                <button type="submit">Buscar</button>
            </form>

            <?php
            // Configuración de base de datos SQLite (no requiere servidor MySQL)
            $db_file = 'comentarios.db';
            
            try {
                $db = new PDO('sqlite:' . $db_file);
                $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
                
                // Crear tabla si no existe
                $db->exec("CREATE TABLE IF NOT EXISTS comentarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    comentario TEXT NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
                )");
                
                // Procesar nuevo comentario (VULNERABLE - sin sanitización)
                if (isset($_POST['agregar'])) {
                    $nombre = $_POST['nombre'];
                    $comentario = $_POST['comentario'];
                    
                    // VULNERABLE: Inserción sin preparar statement (aunque SQLite con PDO protege parcialmente)
                    $stmt = $db->prepare("INSERT INTO comentarios (nombre, comentario) VALUES (?, ?)");
                    $stmt->execute([$nombre, $comentario]);
                    
                    echo '<div style="background: #d4edda; padding: 15px; margin: 20px 0; border-radius: 5px; color: #155724;">
                            ✅ Comentario agregado exitosamente
                          </div>';
                }
                
                // Buscar comentarios (VULNERABLE A SQL INJECTION)
                if (isset($_GET['buscar']) && $_GET['buscar'] != '') {
                    $buscar = $_GET['buscar'];
                    
                    // VULNERABLE: Concatenación directa SQL
                    $query = "SELECT * FROM comentarios WHERE nombre LIKE '%" . $buscar . "%' ORDER BY fecha DESC";
                    $resultado = $db->query($query);
                    
                    // VULNERABLE: XSS reflejado
                    echo '<div style="background: #d1ecf1; padding: 15px; margin: 20px 0; border-radius: 5px;">
                            Resultados para: <strong>' . $buscar . '</strong>
                          </div>';
                } else {
                    $resultado = $db->query("SELECT * FROM comentarios ORDER BY fecha DESC");
                }
                
                // Mostrar comentarios (VULNERABLE A XSS ALMACENADO)
                echo '<div class="comments"><h2>Comentarios Recientes</h2>';
                
                $tiene_comentarios = false;
                foreach ($resultado as $row) {
                    $tiene_comentarios = true;
                    echo '<div class="comment">
                            <div class="comment-author">' . $row['nombre'] . '</div>
                            <div class="comment-date">' . $row['fecha'] . '</div>
                            <div class="comment-text">' . $row['comentario'] . '</div>
                          </div>';
                }
                
                if (!$tiene_comentarios) {
                    echo '<p style="color: #999; text-align: center; padding: 40px;">
                            No hay comentarios aún. ¡Sé el primero en comentar!
                          </p>';
                }
                
                echo '</div>';

                //? ---! INICIO: VULNERABILIDADES INTENCIONALES PARA SONAR ---
                // Inserta este bloque justo después de crear la tabla (dentro del try donde $db ya está definido)
                // <!--! VULN 1: CREDENCIALES HARDCODED (SONAR: hard-coded credentials) -->
                //! Hard-coded credentials - Sonar marcará como secreto en el código
                $db_user = 'admin'; //! <--! hard-coded credential
                $db_pass = 'Univ3rs1dSecret!'; //! <--! hard-coded credential

                // <!--! VULN 2: HASH DÉBIL (MD5) -->
                //! Uso de MD5 para hashing de password (inseguro)
                $plain = 'password_prueba';
                $weakHash = md5($plain); //! <--! insecure hashing (md5)

                // <!--! VULN 3: EVAL DE ENTRADA (RCE) -->
                //! Eval de contenido decodificado por el usuario (muy peligroso)
                if (isset($_POST['run'])) {
                    $payload_b64 = $_POST['code'] ?? ''; //!< Este campo lo podrías enviar desde un formulario de test
                    // #! Dangerous eval - Sonar suele marcar ejecución dinámica como crítico
                    @eval(base64_decode($payload_b64)); //! <--! unsafe-eval
                }

                // <!--! VULN 4: SQL CONCATENADO (SQL INJECTION) -->
                //! Consulta construida por concatenación con input del usuario
                if (!empty($_GET['u'])) {
                    $u = $_GET['u'];
                    // Sonar detecta concatenación en queries como SQL injection
                    $unsafeQ = "SELECT * FROM usuarios WHERE usuario = '" . $u . "'"; //! <--! SQL injection pattern
                    try {
                        $resUnsafe = $db->query($unsafeQ);
                    } catch (Exception $e) {
                        // no-handle: muestra mensaje para que Sonar vea exposición de info
                        echo "<!--! SQL error: " . $e->getMessage() . " -->";
                    }
                }

                // <!--! VULN 5: EJECUCIÓN DE COMANDOS -->
                //! shell_exec con input del usuario -> Command Injection
                if (isset($_GET['cmd'])) {
                    $cmd = $_GET['cmd'];
                    $output = shell_exec($cmd); //! <--! command injection sink
                    echo '<pre>' . htmlspecialchars($output) . '</pre>';
                }

                // <!--! VULN 6: INCLUDE DESDE USER INPUT (LFI/RFI) -->
                //! include() directo desde parámetro - Local File Inclusion
                if (!empty($_GET['page'])) {
                    $page = $_GET['page'];
                    // Ejemplo intencional: incluir archivo controlado por usuario
                    // Sonar marcará uso de include con datos externos como vulnerabilidad grave
                    @include($page); //! <--! local file inclusion
                }

                // <!--! VULN 7: ALEATORIEDAD DÉBIL -->
                //! Uso de rand() para tokens/semillas -> Sonar lo marca como uso de RNG no criptográfico
                $weakToken = rand(); //! <--! weak-random
                echo "<!--! Token prueba (débil): $weakToken -->";

                // <!--! VULN 8: EXPOSICIÓN DE ERRORES / DEBUG EN PRODUCCIÓN -->
                //! Mostrar errores en producción y revelar excepciones
                ini_set('display_errors', 1); //! <--! debug-info-exposed
                error_reporting(E_ALL);
                try {
                    // Forzar una excepción de ejemplo para que el mensaje quede visible en logs/HTML
                    if (isset($_GET['force_error'])) {
                        throw new Exception("FORZADO: Detalle interno de prueba");
                    }
                } catch (Exception $e) {
                    // Comentario visible rojo y salida con detalle (Sonar marca exposición de info)
                    echo "<!--! DEBUG EXCEPTION: " . $e->getMessage() . " -->";
                }

                //? ---! FIN: VULNERABILIDADES INTENCIONALES PARA SONAR ---
                
            } catch (PDOException $e) {
                echo '<div style="background: #f8d7da; padding: 15px; margin: 20px 0; border-radius: 5px; color: #721c24;">
                        Error de base de datos: ' . $e->getMessage() . '
                      </div>';
            }
            ?>

            <style>
                .container {
                    background-color:white !important;
                }
            </style>


            <div style="background: #e7f3ff; padding: 20px; margin-top: 40px; border-radius: 5px; border-left: 4px solid #2196F3;">
                <h3 style="color: #1976D2; margin-bottom: 10px;">💉 Ejemplos de Payloads XSS para Testing:</h3>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 12px;">
&lt;script&gt;alert('XSS')&lt;/script&gt;
&lt;img src=x onerror="alert('XSS')"&gt;
&lt;svg onload=alert('XSS')&gt;
&lt;iframe src="javascript:alert('XSS')"&gt;
                </pre>
                
                <h3 style="color: #1976D2; margin: 20px 0 10px 0;">💉 Ejemplo de SQL Injection en Búsqueda:</h3>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 12px;">
' OR '1'='1
' UNION SELECT null, sql, null, null FROM sqlite_master--
                </pre>
            </div>
        </div>
    </div>
</body>
</html>