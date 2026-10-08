const request = require("supertest");
const { app } = require("../src/app");

test("combined discounts never reduce the total below 50%", async () => {
  const response = await request(app)
    .post("/checkout")
    .send({ price: 100, coupons: [40, 40] });

  expect(response.body.total).toBeGreaterThanOrEqual(50);
});
