# Guía de Despliegue - Molaris | Clínica San Felipe

## 📋 Resumen del Proyecto

- **2 Proyectos Django** que comparten la misma base de datos PostgreSQL:
  - `gestion_clinica`: Sistema de gestión interno (trabajadores)
  - `cliente_web`: Portal web para clientes

## ✅ Estado Actual

- ✅ Migraciones aplicadas en ambos proyectos
- ✅ Base de datos compartida configurada
- ✅ Proyectos funcionando correctamente

## 🚀 Opciones de Despliegue

### Opción 1: Railway (RECOMENDADA para demostración rápida)

**Ventajas:**
- ⚡ **Muy rápido de configurar** (15-30 minutos)
- 💰 **Plan gratuito generoso** (500 horas/mes)
- 🔧 **Configuración simple** con archivos `railway.json`
- 📦 **Despliegue automático** desde GitHub
- 🗄️ **PostgreSQL incluido** (gratis hasta 5GB)
- 🌐 **Dominios gratuitos** (.railway.app)

**Desventajas:**
- ⏰ Puede ser lento si superas el plan gratuito
- 📊 Menos control sobre la infraestructura

**Costo estimado:** $0-5/mes (plan gratuito suele ser suficiente)

**Ideal para:** Demostración rápida, presentación, MVP

---

### Opción 2: AWS (RECOMENDADA para producción)

**Ventajas:**
- 💪 **Muy potente y escalable**
- 🎓 **$50 crédito gratis** (AWS Educate)
- 🔒 **Más control y seguridad**
- 📈 **Escalable a futuro**
- 🗄️ **RDS PostgreSQL** (incluido en crédito)

**Desventajas:**
- ⏱️ **Más tiempo de configuración** (2-4 horas)
- 📚 **Curva de aprendizaje** más alta
- 🔧 **Requiere más configuración manual**

**Costo estimado:** $0-15/mes (con crédito educativo)

**Ideal para:** Producción, proyecto a largo plazo

---

## 🎯 Recomendación Final

### Para tu presentación: **RAILWAY**

**Razones:**
1. ⚡ **Velocidad**: Despliegue en 30 minutos vs 2-4 horas
2. 🎯 **Enfoque**: Puedes concentrarte en la presentación, no en la infraestructura
3. 💰 **Costo**: Gratis para demostración
4. 🔄 **Fácil**: Si algo falla, es fácil de corregir

### Después de la presentación: **AWS**

**Razones:**
1. 💪 **Profesional**: Muestra conocimiento de cloud enterprise
2. 📈 **Escalable**: Si el proyecto crece, AWS puede crecer con él
3. 🎓 **Aprendizaje**: Excelente para tu portafolio
4. 💰 **Crédito**: Tienes $50 gratis para experimentar

---

## 📝 Checklist Pre-Despliegue

### Antes de desplegar, verifica:

- [ ] `DEBUG = False` en ambos `settings.py`
- [ ] `SECRET_KEY` en variables de entorno
- [ ] `ALLOWED_HOSTS` configurado
- [ ] Base de datos PostgreSQL configurada
- [ ] Archivos estáticos configurados (`STATIC_ROOT`, `STATIC_URL`)
- [ ] Archivos media configurados (`MEDIA_ROOT`, `MEDIA_URL`)
- [ ] Variables de entorno (Twilio, etc.) configuradas
- [ ] Migraciones aplicadas en ambos proyectos
- [ ] Superusuario creado
- [ ] Pruebas locales funcionando

---

## 🚀 Próximos Pasos

1. **Elegir plataforma** (Railway recomendado para empezar)
2. **Preparar archivos de configuración** (requirements.txt, Procfile, etc.)
3. **Configurar variables de entorno**
4. **Desplegar base de datos**
5. **Desplegar aplicaciones**
6. **Configurar dominios**
7. **Probar todo**

---

## 📞 ¿Necesitas ayuda?

Una vez que elijas la plataforma, puedo ayudarte con:
- Configuración de archivos de despliegue
- Variables de entorno
- Configuración de base de datos
- Despliegue paso a paso

