const { applyCoupons } = require("../src/cart");

test("applies a single coupon", () => {
  expect(applyCoupons(100, [10])).toBe(90);
});
