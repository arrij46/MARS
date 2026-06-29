import { useEffect, useRef } from "react";

export function useAutoScroll(dependencies) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [dependencies]);

  return ref;
}
