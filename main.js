const fs = require("fs");
const path = require("path");
const http = require("http");
const { Telegraf, Input } = require("telegraf");
require("dotenv").config();

// ═══════════════════════════════════════════════════════
// Переменные окружения
// ═══════════════════════════════════════════════════════

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const CHANNEL_URL = process.env.CHANNEL_URL;
const SITE_URL = "https://satanovski.ru/";

const PDF_PATH = path.join(__dirname, "files", "checklist.pdf");

// ═══════════════════════════════════════════════════════
// Логгер
// ═══════════════════════════════════════════════════════

function log(level, message) {
  const time = new Date().toISOString().replace("T", " ").replace("Z", "");
  console.log(`${time} | ${level} | ${message}`);
}

const logger = {
  info: (msg) => log("INFO", msg),
  error: (msg) => log("ERROR", msg),
};

// ═══════════════════════════════════════════════════════
// Проверка переменных
// ═══════════════════════════════════════════════════════

if (!BOT_TOKEN) {
  throw new Error("Не задана переменная окружения BOT_TOKEN");
}

if (!CHANNEL_ID) {
  throw new Error("Не задана переменная окружения CHANNEL_ID");
}

if (!CHANNEL_URL) {
  throw new Error("Не задана переменная окружения CHANNEL_URL");
}

// ═══════════════════════════════════════════════════════
// Инициализация бота
// ═══════════════════════════════════════════════════════

const bot = new Telegraf(BOT_TOKEN);

let cachedPdfFileId = null;

// ═══════════════════════════════════════════════════════
// Тексты
// ═══════════════════════════════════════════════════════

const WELCOME_TEXT = `👋 Привет, <b>{name}</b>!

Меня зовут <b>Матвей Сатановский</b> — мне 16, и я занимаюсь разработкой, дизайном и видеомонтажом для бизнес-проектов.

<blockquote>16 лет — не повод быть посредственным.
Я амбициозен, заряжен и думаю на годы вперёд. Каждый проект — это вклад в репутацию, поэтому работаю с полной отдачей. Путешествую, читаю, тренируюсь, генерирую идеи — и всё это отражается в том, что я создаю.

Люблю жизнь и наслаждаюсь ей ❤️
</blockquote>

🎁 Специально для тебя я подготовил
<b>бесплатный материал</b>:

📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>

Внутри:
• 10 критических ошибок с реальными примерами
• Готовые решения для каждой проблемы
• Советы, которые можно внедрить уже сегодня

Нажми кнопку ниже, чтобы забрать 👇`;

const NOT_SUBSCRIBED_TEXT = `😔 Ты пока <b>не подписан</b> на канал.

А там — <b>реально много пользы</b>:

🧠 Саморазвитие и мышление
💼 Бизнес, digital и маркетинг
🏋️ Спорт и здоровье
🚀 Личный бренд и рост
✨ Лайфстайл и полезные лайфхаки

📌 <b>Чтобы получить подарок:</b>

1️⃣ Нажми <b>«📢 Перейти на канал»</b>
2️⃣ Подпишись
3️⃣ Вернись и нажми <b>«🔄 Проверить подписку»</b>

И чек-лист — твой! 🎁`;

const SUCCESS_TEXT = `🎉 Отлично, <b>{name}</b>!

Подписка подтверждена ✅
Держи свой подарок 👇

📋 <b>«Чек-лист ТОП-10 ошибок, которые убивают конверсию вашего сайта»</b>

Изучай, внедряй и наблюдай`;

const STILL_NOT_SUBSCRIBED_TEXT = `🤔 Хм, подписки всё ещё нет…

Убедись, что нажал <b>«Подписаться»</b>
в канале, а потом снова нажми
<b>«🔄 Проверить подписку»</b> 👇`;

const SITE_TEXT = `<b>Официальный сайт Матвея Сатановского</b>

Здесь ты найдёшь всё, что я делаю:

🎬 <b>Видеомонтаж</b> — динамичные ролики для бизнеса, рилсы, клипы и контент для соцсетей

💻 <b>Веб-разработка</b> — сайты, лендинги и боты, которые приносят заявки

🎨 <b>Дизайн</b> — визуальные решения, которые выделяют бренд среди конкурентов


Можешь посмотреть портфолио, изучить услуги и сразу оставить заявку.

👇 Переходи и смотри сам:`;

const LOADING_TEXT = "⏳ Секунду, проверяю...";
const FADE_TEXT = "⠀";

// ═══════════════════════════════════════════════════════
// Клавиатуры
// ═══════════════════════════════════════════════════════

function welcomeKeyboard() {
  return {
    inline_keyboard: [
      [
        {
          text: "🎁 Получить материал",
          callback_data: "get_material",
        },
      ],
    ],
  };
}

function subscribeKeyboard() {
  return {
    inline_keyboard: [
      [
        {
          text: "📢 Перейти на канал",
          url: CHANNEL_URL,
        },
      ],
      [
        {
          text: "🔄 Проверить подписку",
          callback_data: "check_subscription",
        },
      ],
    ],
  };
}

function siteKeyboard() {
  return {
    inline_keyboard: [
      [
        {
          text: "🌐 Перейти на сайт",
          url: SITE_URL,
        },
      ],
    ],
  };
}

// ═══════════════════════════════════════════════════════
// Вспомогательные функции
// ═══════════════════════════════════════════════════════

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getUserName(user) {
  return user.first_name || (user.username ? `@${user.username}` : "друг");
}

function getStartArgs(text = "") {
  const parts = text.trim().split(/\s+/);
  return parts.length > 1 ? parts.slice(1).join(" ") : undefined;
}

// ═══════════════════════════════════════════════════════
// Проверка подписки
// ═══════════════════════════════════════════════════════

async function isUserSubscribed(userId) {
  try {
    const member = await bot.telegram.getChatMember(CHANNEL_ID, userId);
    return ["member", "administrator", "creator"].includes(member.status);
  } catch (error) {
    logger.error(
      `Ошибка проверки подписки для ${userId}: ${error.message || error}`
    );
    return false;
  }
}

// ═══════════════════════════════════════════════════════
// Анимация удаления сообщения
// ═══════════════════════════════════════════════════════

async function fadeOut(chatId, messageId) {
  try {
    await bot.telegram.editMessageText(
      chatId,
      messageId,
      undefined,
      LOADING_TEXT,
      { parse_mode: "HTML" }
    );
  } catch (error) {}

  await sleep(700);

  try {
    await bot.telegram.editMessageText(
      chatId,
      messageId,
      undefined,
      FADE_TEXT
    );
  } catch (error) {}

  await sleep(400);

  try {
    await bot.telegram.deleteMessage(chatId, messageId);
  } catch (error) {}

  await sleep(200);
}

// ═══════════════════════════════════════════════════════
// Отправка PDF
// ═══════════════════════════════════════════════════════

async function sendPdf(chatId, name) {
  await bot.telegram.sendMessage(
    chatId,
    SUCCESS_TEXT.replace("{name}", name),
    { parse_mode: "HTML" }
  );

  await sleep(500);

  if (cachedPdfFileId) {
    await bot.telegram.sendDocument(chatId, cachedPdfFileId, {
      caption: "📎 Твой чек-лист готов. Приятного изучения!",
      parse_mode: "HTML",
    });

    logger.info(`📦 PDF отправлен из кэша пользователю ${chatId}`);
  } else {
    const msg = await bot.telegram.sendDocument(
      chatId,
      Input.fromLocalFile(PDF_PATH, "Чек-лист_ТОП-10_ошибок_конверсии.pdf"),
      {
        caption: "📎 Твой чек-лист готов. Приятного изучения!",
        parse_mode: "HTML",
      }
    );

    cachedPdfFileId = msg.document.file_id;

    logger.info(
      `📦 PDF отправлен с диска, file_id сохранён. Пользователь: ${chatId}`
    );
  }
}

// ═══════════════════════════════════════════════════════
// HTTP-сервер для Render health-check
// ═══════════════════════════════════════════════════════

function startHealthServer() {
  const port = Number(process.env.PORT || 10000);

  const server = http.createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("OK");
  });

  server.listen(port, "0.0.0.0", () => {
    logger.info(`🌐 HTTP-сервер запущен на порту ${port}`);
  });
}

// ═══════════════════════════════════════════════════════
// Обработчики команд
// ═══════════════════════════════════════════════════════

bot.start(async (ctx) => {
  const user = ctx.from;
  const name = getUserName(user);
  const source = getStartArgs(ctx.message?.text || "");

  logger.info(
    `Пользователь ${user.id} (${user.username || "no_username"}) нажал /start | source=${source}`
  );

  await ctx.reply(WELCOME_TEXT.replace("{name}", name), {
    parse_mode: "HTML",
    reply_markup: welcomeKeyboard(),
  });
});

bot.command("site", async (ctx) => {
  const user = ctx.from;

  logger.info(
    `Пользователь ${user.id} (${user.username || "no_username"}) нажал /site`
  );

  await ctx.reply(SITE_TEXT, {
    parse_mode: "HTML",
    reply_markup: siteKeyboard(),
  });
});

// ═══════════════════════════════════════════════════════
// Обработчики callback-кнопок
// ═══════════════════════════════════════════════════════

bot.action("get_material", async (ctx) => {
  const user = ctx.from;
  const name = getUserName(user);
  const message = ctx.callbackQuery.message;

  if (!message) return;

  logger.info(`Пользователь ${user.id} нажал «Получить материал»`);

  const subscribed = await isUserSubscribed(user.id);

  await fadeOut(message.chat.id, message.message_id);

  if (subscribed) {
    await sendPdf(message.chat.id, name);
  } else {
    await bot.telegram.sendMessage(message.chat.id, NOT_SUBSCRIBED_TEXT, {
      parse_mode: "HTML",
      reply_markup: subscribeKeyboard(),
    });
  }
});

bot.action("check_subscription", async (ctx) => {
  const user = ctx.from;
  const name = getUserName(user);
  const message = ctx.callbackQuery.message;

  if (!message) return;

  logger.info(`Пользователь ${user.id} нажал «Проверить подписку»`);

  const subscribed = await isUserSubscribed(user.id);

  if (subscribed) {
    await fadeOut(message.chat.id, message.message_id);
    await sendPdf(message.chat.id, name);
  } else {
    await ctx.answerCbQuery("❌ Подписка не найдена!", {
      show_alert: true,
    });

    try {
      await bot.telegram.editMessageText(
        message.chat.id,
        message.message_id,
        undefined,
        STILL_NOT_SUBSCRIBED_TEXT,
        {
          parse_mode: "HTML",
          reply_markup: subscribeKeyboard(),
        }
      );
    } catch (error) {}
  }
});

// ═══════════════════════════════════════════════════════
// Обработка ошибок
// ═══════════════════════════════════════════════════════

bot.catch((error) => {
  logger.error(`Ошибка бота: ${error.message || error}`);
});

// ═══════════════════════════════════════════════════════
// Запуск
// ═══════════════════════════════════════════════════════

async function main() {
  logger.info("🤖 Бот запускается...");

  if (!fs.existsSync(PDF_PATH)) {
    logger.error(`❌ Файл ${PDF_PATH} не найден!`);
    process.exit(1);
  }

  startHealthServer();

  await bot.telegram.deleteWebhook({
    drop_pending_updates: true,
  });

  await bot.launch();

  const me = await bot.telegram.getMe();
  logger.info(`✅ Бот запущен!`);
  logger.info(
    `Run polling for bot @${me.username} id=${me.id} - '${me.first_name}'`
  );
}

main().catch((error) => {
  logger.error(
    `❌ Критическая ошибка запуска: ${error.message || error}`
  );
  process.exit(1);
});

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));