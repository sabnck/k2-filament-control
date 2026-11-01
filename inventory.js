(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.InventoryMath = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function clampGrams(value, capacity = 1000) {
    const grams = Number(value);
    const max = Number(capacity) || 1000;
    if (!Number.isFinite(grams)) return 0;
    return Math.min(max, Math.max(0, Math.round(grams)));
  }

  function consume(current, amount) {
    return clampGrams(Number(current) - Math.max(0, Number(amount) || 0));
  }

  function refill(capacity = 1000) {
    return clampGrams(capacity, capacity);
  }

  return { clampGrams, consume, refill };
});

