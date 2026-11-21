import "@testing-library/jest-dom"

// jsdom has no layout observer; keep responsive chart lifecycles testable.
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class implements ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
