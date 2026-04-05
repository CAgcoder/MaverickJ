import { describe, it, expect } from "vitest";
import { extractJSON } from "../src/llm/responseParser.js";

describe("extractJSON", () => {
  it("should extract JSON from code block", () => {
    const text = '```json\n{"key": "value"}\n```';
    expect(extractJSON(text)).toBe('{"key": "value"}');
  });

  it("should extract JSON from code block without language tag", () => {
    const text = '```\n{"key": "value"}\n```';
    expect(extractJSON(text)).toBe('{"key": "value"}');
  });

  it("should extract raw JSON object", () => {
    const text = 'Here is the result: {"key": "value"}';
    expect(extractJSON(text)).toBe('{"key": "value"}');
  });

  it("should extract raw JSON array", () => {
    const text = '[{"id": 1}]';
    expect(extractJSON(text)).toBe('[{"id": 1}]');
  });

  it("should handle plain JSON", () => {
    const text = '{"agentRole": "advocate", "arguments": []}';
    expect(extractJSON(text)).toBe('{"agentRole": "advocate", "arguments": []}');
  });
});
