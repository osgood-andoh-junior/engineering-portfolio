import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { Classify, Dashboard, Experiments, Models, Tickets, Training } from "@/components/workspace";

const missing = { error: "STUDENT_ML_NOT_IMPLEMENTED", component: "naive_bayes", message: "Complete TODO(STUDENT-ML) in the ML module." };
function response(data: unknown, status = 200) { return new Response(JSON.stringify(data), { status }); }
afterEach(() => vi.unstubAllGlobals());

test("dashboard shows honest empty states", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => response([])));
  render(<Dashboard />);
  expect(await screen.findByText("Not trained")).toBeInTheDocument();
  expect(screen.getByText("Your first prediction starts here")).toBeInTheDocument();
  expect(screen.getByText("No evaluation recorded")).toBeInTheDocument();
});

test("dashboard reports connection failures instead of zero-valued success", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
  render(<Dashboard />);
  expect(await screen.findByRole("alert")).toHaveTextContent("CONNECTION_ERROR");
  expect(screen.queryByText("Not trained")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

test("classification displays the backend development error", async () => {
  const fetchMock = vi.fn().mockResolvedValue(response(missing, 501));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<Classify />);
  expect(screen.getByRole("button", { name: "Classify" })).toBeDisabled();
  await user.type(screen.getByLabelText("Ticket text"), "Wi-Fi unavailable");
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "Classify" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("STUDENT_ML_NOT_IMPLEMENTED");
  expect(screen.getByRole("alert")).toHaveTextContent("Component: naive_bayes");
  expect(screen.queryByText("Confidence")).not.toBeInTheDocument();
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ text: "Wi-Fi unavailable" });
});

test("ticket creation uses the selected label and refreshes the list", async () => {
  const ticket = { id: 1, text: "Account locked", actual_category: "Account", predicted_category: null, confidence: null, model_version: null, created_at: "2026-01-01T00:00:00Z" };
  const fetchMock = vi.fn().mockResolvedValueOnce(response([])).mockResolvedValueOnce(response(ticket, 201)).mockResolvedValueOnce(response([ticket]));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<Tickets />);
  await screen.findByText("A fresh dataset");
  await user.type(screen.getByLabelText("Ticket text"), ticket.text);
  await user.selectOptions(screen.getByLabelText(/Actual category/), "Account");
  await user.click(screen.getByRole("button", { name: "Save ticket" }));
  expect(await screen.findByText("Account locked")).toBeInTheDocument();
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ text: ticket.text, actual_category: "Account" });
});

test("models do not fabricate results", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => response([])));
  render(<Models />);
  expect(await screen.findByText("Your model registry is empty")).toBeInTheDocument();
});

test("training displays failed ML dependency", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response([])).mockResolvedValueOnce(response(missing, 501)).mockResolvedValueOnce(response([])));
  render(<Training />);
  await screen.findByText("No training runs yet");
  await userEvent.click(screen.getByRole("button", { name: "Start training" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("STUDENT_ML_NOT_IMPLEMENTED");
});

test("all six experiment notebooks are discoverable", () => {
  render(<Experiments />);
  expect(screen.getAllByRole("article")).toHaveLength(6);
  expect(screen.getByText("ml/notebooks/01_bow_naive_bayes.ipynb")).toBeInTheDocument();
});

test("ticket editing and deletion use their API routes", async () => {
  const ticket = { id: 7, text: "Old ticket", actual_category: null, predicted_category: null, confidence: null, model_version: null, created_at: "2026-01-01T00:00:00Z" };
  const updated = { ...ticket, text: "Updated ticket", actual_category: "Hardware" };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(response([ticket]))
    .mockResolvedValueOnce(response(updated))
    .mockResolvedValueOnce(response([updated]))
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValueOnce(response([]));
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  render(<Tickets />);
  await user.click(await screen.findByRole("button", { name: "Edit" }));
  await user.clear(screen.getByLabelText("Ticket text"));
  await user.type(screen.getByLabelText("Ticket text"), updated.text);
  await user.selectOptions(screen.getByLabelText(/Actual category/), "Hardware");
  await user.click(screen.getByRole("button", { name: "Save ticket" }));
  await screen.findByText("Updated ticket");
  expect(fetchMock.mock.calls[1][0]).toMatch(/\/api\/tickets\/7$/);
  expect(fetchMock.mock.calls[1][1].method).toBe("PATCH");
  await user.click(screen.getByRole("button", { name: "Delete" }));
  expect(await screen.findByText("A fresh dataset")).toBeInTheDocument();
  expect(fetchMock.mock.calls[3][1].method).toBe("DELETE");
  vi.restoreAllMocks();
});

test("classification saves once before displaying an ML failure", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(response({ id: 9 }, 201)).mockResolvedValueOnce(response(missing, 501));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<Classify />);
  await user.type(screen.getByLabelText("Ticket text"), "Support request");
  await user.click(screen.getByRole("button", { name: "Classify" }));
  await screen.findByRole("alert");
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ ticket_id: 9 });
  expect(screen.getByText(/Saved tickets remain/)).toBeInTheDocument();
});

test("prediction result renders values supplied by the API fixture", async () => {
  // Canned UI fixture only; never an application prediction fallback.
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response({ category: "Other", confidence: 0.5, model: "test-only", processing_time_ms: 12 })));
  const user = userEvent.setup();
  render(<Classify />);
  await user.type(screen.getByLabelText("Ticket text"), "Fixture");
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "Classify" }));
  expect(await screen.findByText("50.0%")).toBeInTheDocument();
  expect(screen.getByText("test-only")).toBeInTheDocument();
  expect(screen.getByText("12.00 ms")).toBeInTheDocument();
});
