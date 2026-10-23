/** Интерфейс сайта курсов «Корочки.есть» на React. */
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  erasePhoneSeparator,
  formatPhone,
  phoneCaretPosition,
} from "./phone.js";
import "./style.css";

const slides = [
  {
    image: "/slides/code.svg",
    label: "01 / 04",
    title: "Начните с идеи",
    text: "Поймите, как устроены алгоритмы, и соберите свой первый проект.",
  },
  {
    image: "/slides/design.svg",
    label: "02 / 04",
    title: "Думайте о людях",
    text: "Учитесь создавать ясные и удобные цифровые интерфейсы.",
  },
  {
    image: "/slides/data.svg",
    label: "03 / 04",
    title: "Наводите порядок",
    text: "Разберитесь со связями, данными и надёжным хранением.",
  },
  {
    image: "/slides/growth.svg",
    label: "04 / 04",
    title: "Двигайтесь дальше",
    text: "Выберите программу и оставьте заявку на удобную дату.",
  },
];

/** Возвращает завтрашнюю дату по местному времени посетителя. */
function tomorrow() {
  const day = new Date();
  day.setDate(day.getDate() + 1);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

/** Обрабатывает ответ API и показывает понятные ошибки сервера. */
async function api(path, options = {}, csrf = "") {
  const response = await fetch(`/api/${path}`, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
      ...options.headers,
    },
  });
  const data = await response.json();
  if (!response.ok) throw data;
  return data;
}

/** Выводит поле ввода с подписью и сообщением об ошибке. */
function Field({ label, name, errors, hint, ...props }) {
  const id = `field-${name}`;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={name}
        required
        aria-invalid={Boolean(errors?.[name])}
        aria-describedby={
          errors?.[name] ? `${id}-error` : hint ? `${id}-hint` : undefined
        }
        {...props}
      />
      {hint && !errors?.[name] && <small id={`${id}-hint`}>{hint}</small>}
      {errors?.[name] && (
        <small id={`${id}-error`} className="field-error">
          {errors[name]}
        </small>
      )}
    </div>
  );
}

/** Выводит поле телефона с автоматической расстановкой разделителей. */
function PhoneField({ errors }) {
  const [phone, setPhone] = useState("");

  /** Форматирует введённые цифры и сохраняет положение курсора. */
  function changePhone(event) {
    const input = event.currentTarget;
    const raw = input.value;
    const digits = raw.replace(/\D/g, "");
    const addedPrefix =
      digits && digits[0] !== "7" && digits[0] !== "8" ? 1 : 0;
    const digitCount =
      raw.slice(0, input.selectionStart ?? raw.length).replace(/\D/g, "")
        .length + addedPrefix;
    const formatted = formatPhone(raw);
    setPhone(formatted);
    requestAnimationFrame(() => {
      if (!input.isConnected) return;
      const caret = phoneCaretPosition(formatted, digitCount);
      input.setSelectionRange(caret, caret);
    });
  }

  /** Удаляет цифру при нажатии Backspace рядом со скобкой или дефисом. */
  function backspacePhone(event) {
    const input = event.currentTarget;
    if (
      event.key !== "Backspace" ||
      input.selectionStart !== input.selectionEnd
    )
      return;
    const replacement = erasePhoneSeparator(phone, input.selectionStart);
    if (replacement === null) return;
    event.preventDefault();
    const digitCount =
      phone.slice(0, input.selectionStart).replace(/\D/g, "").length - 1;
    setPhone(replacement);
    requestAnimationFrame(() => {
      if (!input.isConnected) return;
      const caret = phoneCaretPosition(replacement, digitCount);
      input.setSelectionRange(caret, caret);
    });
  }

  return (
    <Field
      label="Телефон"
      name="phone"
      type="tel"
      inputMode="numeric"
      autoComplete="off"
      pattern="8\([0-9]{3}\)[0-9]{3}-[0-9]{2}-[0-9]{2}"
      placeholder="8(999)999-99-99"
      hint="Введите цифры — скобки и дефисы появятся сами"
      errors={errors}
      value={phone}
      onChange={changePhone}
      onKeyDown={backspacePhone}
    />
  );
}

/** Управляет переходами между страницами сайта. */
function App() {
  const [page, setPage] = useState(location.hash.slice(1) || "home");
  const [session, setSession] = useState({
    user: null,
    staff: false,
    csrf: "",
  });
  const [courses, setCourses] = useState([]);
  const [applications, setApplications] = useState([]);
  const [adminItems, setAdminItems] = useState({
    applications: [],
    page: 1,
    pages: 1,
    total: 0,
  });
  const [filter, setFilter] = useState("");
  const [adminPage, setAdminPage] = useState(1);
  const [slide, setSlide] = useState(0);
  const [cookie, setCookie] = useState(false);
  const [notice, setNotice] = useState("");
  const [errors, setErrors] = useState({});
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState(null);

  useEffect(() => {
    const onHash = () => {
      const target = location.hash.slice(1) || "home";
      setPage(target === "how" ? "home" : target);
      setErrors({});
      if (target === "how")
        setTimeout(() => document.getElementById("how")?.scrollIntoView(), 0);
      else window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    api("session")
      .then((data) => {
        setSession(data);
        setCookie(!data.cookie_ack);
      })
      .catch(() =>
        setNotice(
          "Не удалось подключиться к серверу. Проверьте запуск Django.",
        ),
      );
    api("courses")
      .then((data) => setCourses(data.courses))
      .catch(() => {});
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      return undefined;
    const timer = setInterval(
      () => setSlide((index) => (index + 1) % slides.length),
      3000,
    );
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (page === "my" && session.user)
      api("applications")
        .then((data) => setApplications(data.applications))
        .catch(showError);
    if (page === "admin" && session.staff) loadAdmin();
  }, [page, session.user, session.staff, filter, adminPage]);

  /** Показывает ответ сервера без технических подробностей. */
  function showError(error) {
    setErrors(error.fields || {});
    setNotice(
      error.error || "Не удалось выполнить действие. Попробуйте ещё раз.",
    );
  }

  /** Обновляет состояние сессии после входа или выхода. */
  async function refreshSession() {
    const data = await api("session");
    setSession(data);
    return data;
  }

  /** Загружает страницу заявок с учётом фильтра администратора. */
  async function loadAdmin() {
    try {
      setAdminItems(
        await api(`admin/applications?page=${adminPage}&status=${filter}`),
      );
    } catch (error) {
      showError(error);
    }
  }

  /** Отправляет данные формы в JSON и открывает нужную страницу. */
  async function submit(
    event,
    endpoint,
    destination,
    transform = (values) => values,
  ) {
    event.preventDefault();
    setNotice("");
    setErrors({});
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api(
        endpoint,
        { method: "POST", body: JSON.stringify(transform(values)) },
        session.csrf,
      );
      let next = destination;
      if (endpoint === "register" || endpoint === "login") {
        const current = await refreshSession();
        if (endpoint === "login" && current.staff) next = "admin";
      }
      location.hash = next;
      if (location.hash === `#${next}`) setPage(next);
      setNotice("Готово! Данные сохранены.");
    } catch (error) {
      showError(error);
    }
  }

  /** Выполняет выход и очищает личные данные на экране. */
  async function signOut() {
    try {
      await api("logout", { method: "POST", body: "{}" }, session.csrf);
      await refreshSession();
      setApplications([]);
      location.hash = "home";
    } catch (error) {
      showError(error);
    }
  }

  /** Ищет курсы по введённому названию. */
  async function search(event) {
    event.preventDefault();
    setNotice("");
    try {
      const data = await api(
        `search?q=${encodeURIComponent(searchTerm.trim())}`,
      );
      setResults(data.courses);
      location.hash = "courses";
    } catch (error) {
      showError(error);
    }
  }

  /** Переводит заявку в следующий разрешённый статус. */
  async function advance(item) {
    const status = item.status === "new" ? "active" : "done";
    try {
      await api(
        `admin/applications/${item.id}/status`,
        { method: "POST", body: JSON.stringify({ status }) },
        session.csrf,
      );
      await loadAdmin();
      setNotice("Статус обновлён.");
    } catch (error) {
      showError(error);
    }
  }

  /** Сохраняет отзыв после завершения обучения. */
  async function sendReview(event, id) {
    event.preventDefault();
    setNotice("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api(
        `applications/${id}/review`,
        { method: "POST", body: JSON.stringify(values) },
        session.csrf,
      );
      const data = await api("applications");
      setApplications(data.applications);
      setNotice("Спасибо за отзыв!");
    } catch (error) {
      showError(error);
    }
  }

  const chosen = slides[slide];
  return (
    <>
      <a className="skip-link" href="#main">
        Перейти к содержимому
      </a>
      <header className="site-header">
        <a href="#home" className="brand" aria-label="Корочки.есть — главная">
          <span className="brand-mark">
            К<span>•</span>
          </span>
          <span>
            Корочки<span className="brand-accent">.есть</span>
          </span>
        </a>
        <nav aria-label="Основная навигация">
          <a
            href="#courses"
            aria-current={page === "courses" ? "page" : undefined}
          >
            Курсы
          </a>
          {session.user && (
            <a href="#my" aria-current={page === "my" ? "page" : undefined}>
              Мои заявки
            </a>
          )}
          {session.staff && (
            <a
              href="#admin"
              aria-current={page === "admin" ? "page" : undefined}
            >
              Панель
            </a>
          )}
        </nav>
        <div className="header-actions">
          {session.user ? (
            <>
              <span className="username">{session.user}</span>
              <button className="text-button" onClick={signOut}>
                Выйти
              </button>
            </>
          ) : (
            <a className="button button-small button-outline" href="#login">
              Войти
            </a>
          )}
        </div>
      </header>

      <main id="main">
        {notice && (
          <div className="notice" role="status">
            {notice}
            <button
              type="button"
              aria-label="Закрыть сообщение"
              onClick={() => setNotice("")}
            >
              ×
            </button>
          </div>
        )}

        {page === "home" && (
          <>
            <section className="hero shell">
              <div className="hero-copy">
                <div className="eyebrow">
                  <span className="eyebrow-line" /> Онлайн-курсы / новый старт
                </div>
                <h1>
                  Новые навыки.
                  <br />
                  <em>Новый старт.</em>
                </h1>
                <p>
                  Выберите направление, отправьте заявку и следите за обучением
                  в личном кабинете. Всё по шагам и в одном месте.
                </p>
                <div className="hero-actions">
                  <a className="button" href="#courses">
                    Выбрать курс <span aria-hidden="true">↗</span>
                  </a>
                  <a className="plain-link" href="#how">
                    Как это работает <span aria-hidden="true">↓</span>
                  </a>
                </div>
                <div className="hero-detail">
                  <span className="detail-icon" aria-hidden="true">
                    ✳
                  </span>
                  <span>03 направления · один понятный старт</span>
                </div>
              </div>
              <div className="hero-art">
                <img src={chosen.image} alt="" />
                <div className="art-caption">
                  <span>{chosen.label}</span>
                  <strong>{chosen.title}</strong>
                  <p>{chosen.text}</p>
                </div>
                <div className="slide-controls">
                  <button
                    type="button"
                    aria-label="Предыдущий слайд"
                    onClick={() => setSlide((slide + 3) % 4)}
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    aria-label="Следующий слайд"
                    onClick={() => setSlide((slide + 1) % 4)}
                  >
                    →
                  </button>
                </div>
              </div>
            </section>
            <section className="course-section shell" id="featured">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Программы обучения</span>
                  <h2>Выберите направление</h2>
                </div>
                <a className="plain-link" href="#courses">
                  Все курсы <span aria-hidden="true">↗</span>
                </a>
              </div>
              <div className="course-grid">
                {courses.map((course, index) => (
                  <article className="course-card" key={course.id}>
                    <div
                      className={`course-symbol symbol-${index}`}
                      aria-hidden="true"
                    >
                      {["⌘", "◈", "▦"][index]}
                    </div>
                    <span className="card-number">0{index + 1} / 03</span>
                    <h3>{course.title}</h3>
                    <p>{course.description}</p>
                    <a
                      href={session.user ? "#apply" : "#register"}
                      aria-label={`Подать заявку: ${course.title}`}
                    >
                      Подробнее <span aria-hidden="true">↗</span>
                    </a>
                  </article>
                ))}
              </div>
            </section>
            <section className="steps-section" id="how">
              <div className="shell">
                <span className="eyebrow">Как это работает</span>
                <h2>
                  От выбора курса
                  <br />
                  до <em>нового навыка</em>
                </h2>
                <div className="steps">
                  <div>
                    <span>01</span>
                    <h3>Создайте аккаунт</h3>
                    <p>Укажите данные один раз, чтобы следить за заявками.</p>
                  </div>
                  <div>
                    <span>02</span>
                    <h3>Выберите программу</h3>
                    <p>Отметьте курс, дату начала и удобный способ оплаты.</p>
                  </div>
                  <div>
                    <span>03</span>
                    <h3>Следите за статусом</h3>
                    <p>Мы покажем, на каком этапе находится ваша заявка.</p>
                  </div>
                </div>
              </div>
            </section>
            <section className="cta shell">
              <div>
                <span className="eyebrow">Готовы начать?</span>
                <h2>
                  Время перейти
                  <br />к делу.
                </h2>
              </div>
              <a
                className="button button-light"
                href={session.user ? "#apply" : "#register"}
              >
                Оставить заявку <span aria-hidden="true">↗</span>
              </a>
            </section>
          </>
        )}

        {page === "courses" && (
          <section className="inner shell">
            <span className="eyebrow">Каталог</span>
            <h1>Курсы для вашего развития</h1>
            <p className="lead">
              Три понятных направления. Выберите то, что интересно именно вам.
            </p>
            <form className="search" autoComplete="off" onSubmit={search}>
              <label htmlFor="search-input">Поиск по названию курса</label>
              <div>
                <input
                  id="search-input"
                  value={searchTerm}
                  minLength="2"
                  maxLength="50"
                  required
                  placeholder="Например, веб-дизайн"
                  onChange={(event) => setSearchTerm(event.target.value)}
                />
                <button className="button" type="submit">
                  Поиск по сайту
                </button>
              </div>
            </form>
            <div className="course-grid">
              {(results ?? courses).map((course, index) => (
                <article className="course-card" key={course.id}>
                  <div
                    className={`course-symbol symbol-${index % 3}`}
                    aria-hidden="true"
                  >
                    {["⌘", "◈", "▦"][index % 3]}
                  </div>
                  <span className="card-number">НАПРАВЛЕНИЕ</span>
                  <h2>{course.title}</h2>
                  <p>{course.description}</p>
                  <a href={session.user ? "#apply" : "#register"}>
                    Записаться <span aria-hidden="true">↗</span>
                  </a>
                </article>
              ))}
            </div>
            {results?.length === 0 && (
              <p role="status">По вашему запросу курсы не найдены.</p>
            )}
            {results && (
              <button
                className="text-button reset-search"
                onClick={() => {
                  setResults(null);
                  setSearchTerm("");
                }}
              >
                Показать все курсы
              </button>
            )}
          </section>
        )}

        {page === "register" && (
          <section className="inner shell form-layout">
            <div className="form-intro">
              <span className="eyebrow">Новый аккаунт</span>
              <h1>
                Добро пожаловать
                <br />
                <em>в Корочки.есть</em>
              </h1>
              <p>
                Создайте аккаунт, чтобы выбрать курс и отслеживать обучение.
              </p>
            </div>
            <form
              className="panel"
              autoComplete="off"
              onSubmit={(event) =>
                submit(event, "register", "my", (values) => ({
                  ...values,
                  consent: values.consent === "on",
                }))
              }
            >
              <h2>Регистрация</h2>
              <div className="form-grid">
                <Field
                  label="Логин"
                  name="username"
                  minLength="6"
                  maxLength="20"
                  pattern="[A-Za-z]{6,20}"
                  hint="6–20 латинских букв"
                  errors={errors}
                />
                <Field
                  label="Фамилия"
                  name="surname"
                  maxLength="20"
                  hint="Русские буквы, первая — заглавная"
                  errors={errors}
                />
                <Field
                  label="Имя"
                  name="given_name"
                  maxLength="20"
                  hint="Русские буквы, первая — заглавная"
                  errors={errors}
                />
                <Field
                  label="Отчество"
                  name="patronymic"
                  maxLength="20"
                  hint="Русские буквы, первая — заглавная"
                  errors={errors}
                />
                <PhoneField errors={errors} />
                <Field
                  label="Электронная почта"
                  name="email"
                  type="email"
                  maxLength="20"
                  errors={errors}
                />
                <div className="wide">
                  <Field
                    label="Почтовый адрес"
                    name="address"
                    maxLength="100"
                    errors={errors}
                  />
                </div>
                <div className="wide">
                  <Field
                    label="Пароль"
                    name="password"
                    type="password"
                    minLength="8"
                    hint="Латинские буквы разного регистра, цифра и символ из $#@!"
                    errors={errors}
                  />
                </div>
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  name="consent"
                  required
                  aria-invalid={Boolean(errors.consent)}
                />
                <span>
                  Согласие на{" "}
                  <a href="#consent">обработку персональных данных</a>
                </span>
              </label>
              {errors.consent && (
                <small className="field-error">{errors.consent}</small>
              )}
              <button className="button full" type="submit">
                Зарегистрироваться <span aria-hidden="true">↗</span>
              </button>
              <p className="form-foot">
                Уже есть аккаунт? <a href="#login">Войти</a>
              </p>
            </form>
          </section>
        )}

        {page === "login" && (
          <section className="inner shell form-layout">
            <div className="form-intro">
              <span className="eyebrow">С возвращением</span>
              <h1>
                Продолжим
                <br />
                <em>с того места</em>
              </h1>
              <p>Войдите, чтобы увидеть свои заявки и продолжить обучение.</p>
            </div>
            <form
              className="panel"
              autoComplete="off"
              onSubmit={(event) => submit(event, "login", "my")}
            >
              <h2>Вход в аккаунт</h2>
              <Field label="Логин" name="username" required errors={errors} />
              <Field
                label="Пароль"
                name="password"
                type="password"
                required
                errors={errors}
              />
              <button className="button full" type="submit">
                Войти <span aria-hidden="true">↗</span>
              </button>
              <p className="form-foot">
                Еще не зарегистрированы? <a href="#register">Регистрация</a>
              </p>
            </form>
          </section>
        )}

        {page === "apply" && (
          <section className="inner shell form-layout">
            <div className="form-intro">
              <span className="eyebrow">Ваша заявка</span>
              <h1>
                Первый шаг
                <br />
                <em>уже сделан</em>
              </h1>
              <p>
                Выберите программу и дату. Администратор рассмотрит заявку, а
                статус появится в личном кабинете.
              </p>
            </div>
            {session.user ? (
              <form
                className="panel"
                autoComplete="off"
                onSubmit={(event) =>
                  submit(event, "applications", "my", (values) => ({
                    ...values,
                    course_id: Number(values.course_id),
                  }))
                }
              >
                <h2>Запись на курс</h2>
                <div className="field">
                  <label htmlFor="course">Программа обучения</label>
                  <select id="course" name="course_id" required defaultValue="">
                    <option value="" disabled>
                      Выберите курс
                    </option>
                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.title}
                      </option>
                    ))}
                  </select>
                </div>
                <Field
                  label="Желаемая дата начала"
                  name="start_date"
                  type="date"
                  min={tomorrow()}
                  errors={errors}
                />
                <div className="field">
                  <label htmlFor="payment">Способ оплаты</label>
                  <select id="payment" name="payment" required defaultValue="">
                    <option value="" disabled>
                      Выберите способ
                    </option>
                    <option value="cash">Наличными</option>
                    <option value="transfer">
                      Переводом по номеру телефона
                    </option>
                  </select>
                </div>
                <p className="form-note">
                  Оплата на сайте не производится. Выбор способа сохраняется в
                  заявке.
                </p>
                <button className="button full" type="submit">
                  Отправить заявку <span aria-hidden="true">↗</span>
                </button>
              </form>
            ) : (
              <div className="panel">
                <h2>Сначала войдите</h2>
                <p>Для подачи заявки нужен аккаунт.</p>
                <a className="button" href="#login">
                  Войти
                </a>
              </div>
            )}
          </section>
        )}

        {page === "my" && (
          <section className="inner shell">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Личный кабинет</span>
                <h1>Мои заявки</h1>
              </div>
              <a className="button" href="#apply">
                Новая заявка <span aria-hidden="true">↗</span>
              </a>
            </div>
            {session.user ? (
              applications.length ? (
                <div className="application-list">
                  {applications.map((item) => (
                    <article className="application-card" key={item.id}>
                      <div>
                        <span className="card-number">ЗАЯВКА №{item.id}</span>
                        <h2>{item.course}</h2>
                        <p>
                          Начало:{" "}
                          {new Date(
                            `${item.start_date}T00:00:00`,
                          ).toLocaleDateString("ru-RU")}{" "}
                          ·{" "}
                          {item.payment === "cash"
                            ? "Наличными"
                            : "Переводом по номеру телефона"}
                        </p>
                      </div>
                      <div className="application-side">
                        <span className={`status status-${item.status}`}>
                          {item.status_label}
                        </span>
                        {item.status === "done" && !item.review && (
                          <form
                            className="review-form"
                            autoComplete="off"
                            onSubmit={(event) => sendReview(event, item.id)}
                          >
                            <label htmlFor={`rating-${item.id}`}>Оценка</label>
                            <select
                              id={`rating-${item.id}`}
                              name="rating"
                              required
                              defaultValue=""
                            >
                              <option value="" disabled>
                                Выберите
                              </option>
                              {[1, 2, 3, 4, 5].map((n) => (
                                <option key={n} value={n}>
                                  {n}
                                </option>
                              ))}
                            </select>
                            <label htmlFor={`review-${item.id}`}>Отзыв</label>
                            <textarea
                              id={`review-${item.id}`}
                              name="text"
                              required
                              maxLength="1000"
                              rows="3"
                            />
                            <button
                              type="submit"
                              className="button button-small"
                            >
                              Отправить отзыв
                            </button>
                          </form>
                        )}
                        {item.review && (
                          <p className="review-saved">
                            Ваш отзыв: {item.review.rating}/5 —{" "}
                            {item.review.text}
                          </p>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty">
                  <span aria-hidden="true">✳</span>
                  <h2>Заявок пока нет</h2>
                  <p>Выберите курс и начните свой путь к новым знаниям.</p>
                  <a className="button" href="#courses">
                    Выбрать курс
                  </a>
                </div>
              )
            ) : (
              <div className="empty">
                <h2>Войдите в аккаунт</h2>
                <a className="button" href="#login">
                  Войти
                </a>
              </div>
            )}
          </section>
        )}

        {page === "admin" && (
          <section className="inner shell">
            <span className="eyebrow">Администрирование</span>
            <h1>Заявки слушателей</h1>
            {session.staff ? (
              <>
                <div className="admin-toolbar">
                  <label htmlFor="status-filter">Статус</label>
                  <select
                    id="status-filter"
                    value={filter}
                    onChange={(event) => {
                      setFilter(event.target.value);
                      setAdminPage(1);
                    }}
                  >
                    <option value="">Все заявки</option>
                    <option value="new">Новая</option>
                    <option value="active">Идет обучение</option>
                    <option value="done">Обучение завершено</option>
                  </select>
                  <span>Всего: {adminItems.total}</span>
                </div>
                <div className="application-list">
                  {adminItems.applications.map((item) => (
                    <article className="application-card" key={item.id}>
                      <div>
                        <span className="card-number">
                          ЗАЯВКА №{item.id} · {item.username}
                        </span>
                        <h2>{item.course}</h2>
                        <p>
                          Начало:{" "}
                          {new Date(
                            `${item.start_date}T00:00:00`,
                          ).toLocaleDateString("ru-RU")}
                        </p>
                      </div>
                      <div className="application-side">
                        <span className={`status status-${item.status}`}>
                          {item.status_label}
                        </span>
                        {item.status !== "done" && (
                          <button
                            className="button button-small"
                            onClick={() => advance(item)}
                          >
                            Перевести:{" "}
                            {item.status === "new"
                              ? "Идет обучение"
                              : "Обучение завершено"}
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
                {adminItems.applications.length === 0 && (
                  <p>Заявок пока нет.</p>
                )}
                <div className="pagination">
                  <button
                    disabled={adminPage <= 1}
                    onClick={() => setAdminPage(adminPage - 1)}
                  >
                    ← Назад
                  </button>
                  <span>
                    Страница {adminItems.page} из {adminItems.pages}
                  </span>
                  <button
                    disabled={adminPage >= adminItems.pages}
                    onClick={() => setAdminPage(adminPage + 1)}
                  >
                    Вперёд →
                  </button>
                </div>
              </>
            ) : (
              <p>Эта страница доступна администратору.</p>
            )}
          </section>
        )}

        {["consent", "privacy", "cookies"].includes(page) && (
          <section className="inner shell legal">
            <span className="eyebrow">Документы</span>
            <h1>
              {page === "consent"
                ? "Согласие на обработку данных"
                : page === "privacy"
                  ? "Политика обработки данных"
                  : "Политика cookie"}
            </h1>
            {page === "consent" ? (
              <>
                <p>
                  Регистрируясь, вы соглашаетесь на обработку указанных в форме
                  имени, фамилии, отчества, телефона, электронной почты и адреса
                  для создания аккаунта, приёма заявок и связи по обучению.
                </p>
                <p>
                  Согласие фиксируется при регистрации. Для отзыва согласия и
                  удаления данных обратитесь к оператору проекта через контакты
                  образовательной организации.
                </p>
              </>
            ) : page === "privacy" ? (
              <>
                <p>
                  Данные используются для регистрации, рассмотрения заявок и
                  отображения статуса обучения. Доступ к заявкам имеет их
                  владелец и администратор. Пароли хранятся в виде хеша, личные
                  поля шифруются.
                </p>
                <p>
                  Учебный прототип не отправляет данные платёжным сервисам. До
                  начала реальной эксплуатации оператор должен заполнить
                  реквизиты, адрес для обращений и сроки хранения данных.
                </p>
              </>
            ) : (
              <>
                <p>
                  Сайт использует необходимые cookie для серверной сессии,
                  защиты форм от подделки запроса и сохранения факта
                  ознакомления с уведомлением. Рекламные и аналитические cookie
                  не применяются.
                </p>
                <p>
                  Отключение обязательных cookie в браузере может помешать входу
                  и отправке форм.
                </p>
              </>
            )}
          </section>
        )}
      </main>

      <footer>
        <div className="shell footer-grid">
          <div>
            <a href="#home" className="brand">
              <span className="brand-mark">
                К<span>•</span>
              </span>
              <span>
                Корочки<span className="brand-accent">.есть</span>
              </span>
            </a>
            <p>Курсы и заявки — в одном месте.</p>
          </div>
          <div>
            <strong>Навигация</strong>
            <a href="#courses">Курсы</a>
            <a href="#how">Как это работает</a>
            <a href="#my">Мои заявки</a>
          </div>
          <div>
            <strong>Документы</strong>
            <a href="#privacy">Обработка данных</a>
            <a href="#consent">Согласие</a>
            <a href="#cookies">Cookie</a>
          </div>
          <span className="copyright">
            © 2026 Корочки.есть. Учебный проект.
          </span>
        </div>
      </footer>

      {cookie && (
        <div
          className="cookie-banner"
          role="dialog"
          aria-label="Уведомление о cookie"
        >
          <div>
            <strong>Мы используем cookie</strong>
            <p>
              Они нужны для входа, защиты форм и сохранения этого уведомления.{" "}
              <a href="#cookies">Подробнее</a>
            </p>
          </div>
          <button
            className="button button-small"
            onClick={async () => {
              try {
                await api(
                  "cookie-ack",
                  { method: "POST", body: "{}" },
                  session.csrf,
                );
                setCookie(false);
              } catch (error) {
                showError(error);
              }
            }}
          >
            Понятно
          </button>
        </div>
      )}
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
