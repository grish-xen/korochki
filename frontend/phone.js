/** Приводит введённый или вставленный номер к виду 8(999)999-99-99. */
export function formatPhone(value) {
  const digits = value.replace(/\D/g, "");
  if (!digits) return "";

  const local = (
    digits[0] === "7" || digits[0] === "8" ? digits.slice(1) : digits
  ).slice(0, 10);
  let phone = "8";
  if (local) phone += `(${local.slice(0, 3)}`;
  if (local.length >= 3) phone += ")";
  if (local.length > 3) phone += local.slice(3, 6);
  if (local.length > 6) phone += `-${local.slice(6, 8)}`;
  if (local.length > 8) phone += `-${local.slice(8, 10)}`;
  return phone;
}

/** Ставит курсор после нужной цифры и следующих за ней разделителей. */
export function phoneCaretPosition(value, digitCount) {
  if (!digitCount) return 0;
  let seen = 0;
  let position = 0;
  while (position < value.length && seen < digitCount) {
    if (/\d/.test(value[position])) seen += 1;
    position += 1;
  }
  while (position < value.length && /\D/.test(value[position])) position += 1;
  return position;
}

/** Удаляет предыдущую цифру, если Backspace нажат после разделителя. */
export function erasePhoneSeparator(value, caret) {
  if (caret < 1 || /\d/.test(value[caret - 1])) return null;
  const before = value.slice(0, caret);
  const digit = before.search(/\d\D*$/);
  if (digit < 0) return null;
  return formatPhone(before.slice(0, digit) + value.slice(caret));
}
