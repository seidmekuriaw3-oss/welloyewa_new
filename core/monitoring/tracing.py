# ============================
# WOLLOYEWA STORE BOT - DISTRIBUTED TRACING
# ============================
"""OpenTelemetry distributed tracing for request tracking."""

import uuid
import time
from contextvars import ContextVar
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings
from core.logger import logger, LoggerContext

# Context variable for current trace
current_trace_id: ContextVar[Optional[str]] = ContextVar('current_trace_id', default=None)
current_span_id: ContextVar[Optional[str]] = ContextVar('current_span_id', default=None)


@dataclass
class Span:
    """Represents a single span in a trace."""
    
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)
    status: str = "ok"
    error_message: Optional[str] = None
    
    def finish(self) -> None:
        """Mark span as finished."""
        self.end_time = time.time()
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        self.attributes[key] = value
    
    def set_error(self, error: Exception) -> None:
        """Mark span as failed with error."""
        self.status = "error"
        self.error_message = str(error)
        self.set_attribute("error.type", type(error).__name__)
        self.set_attribute("error.message", str(error))
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    @property
    def is_finished(self) -> bool:
        """Check if span is finished."""
        return self.end_time is not None


@dataclass
class Trace:
    """Represents a complete trace with multiple spans."""
    
    trace_id: str
    name: str
    start_time: float = field(default_factory=time.time)
    spans: list = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def add_span(self, span: Span) -> None:
        """Add a span to the trace."""
        self.spans.append(span)
    
    def finish(self) -> None:
        """Finish the trace."""
        pass
    
    @property
    def duration_ms(self) -> float:
        """Get trace duration in milliseconds."""
        if not self.spans:
            return 0
        first_span_start = min(s.start_time for s in self.spans)
        last_span_end = max(s.end_time or time.time() for s in self.spans)
        return (last_span_end - first_span_start) * 1000


class Tracer:
    """
    Distributed tracer for tracking requests across services.
    
    Supports:
    - Trace ID propagation
    - Span hierarchy
    - Attribute and event logging
    - Export to observability backends
    """
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or settings.PROJECT_NAME
        self._traces: Dict[str, Trace] = {}
        self._current_trace: Optional[Trace] = None
        self._current_span: Optional[Span] = None
        self._enabled = settings.OTEL_TRACING_ENABLED
    
    def start_trace(self, name: str, attributes: Dict[str, Any] = None) -> Trace:
        """
        Start a new trace.
        
        Args:
            name: Trace name
            attributes: Initial attributes
            
        Returns:
            New Trace object
        """
        trace_id = str(uuid.uuid4())
        trace = Trace(
            trace_id=trace_id,
            name=name,
            attributes=attributes or {},
        )
        
        self._traces[trace_id] = trace
        self._current_trace = trace
        current_trace_id.set(trace_id)
        
        logger.debug(f"Started trace: {name} (ID: {trace_id})")
        return trace
    
    def start_span(
        self,
        name: str,
        parent_span: Optional[Span] = None,
        attributes: Dict[str, Any] = None,
    ) -> Span:
        """
        Start a new span within the current trace.
        
        Args:
            name: Span name
            parent_span: Parent span (defaults to current span)
            attributes: Initial attributes
            
        Returns:
            New Span object
        """
        trace_id = current_trace_id.get()
        
        if not trace_id or trace_id not in self._traces:
            # No active trace, start a new one
            trace = self.start_trace(name, attributes)
            trace_id = trace.trace_id
        
        trace = self._traces[trace_id]
        span_id = str(uuid.uuid4())
        parent_id = parent_span.span_id if parent_span else current_span_id.get()
        
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            attributes=attributes or {},
        )
        
        trace.add_span(span)
        self._current_span = span
        current_span_id.set(span_id)
        
        logger.debug(f"Started span: {name} (ID: {span_id})")
        return span
    
    def finish_span(self, span: Span = None) -> None:
        """Finish the current span or specified span."""
        span = span or self._current_span
        if span:
            span.finish()
            self._current_span = None
            current_span_id.set(None)
            logger.debug(f"Finished span: {span.name} (Duration: {span.duration_ms:.2f}ms)")
    
    def finish_trace(self, trace_id: str = None) -> None:
        """Finish the current trace or specified trace."""
        trace_id = trace_id or current_trace_id.get()
        
        if trace_id and trace_id in self._traces:
            trace = self._traces[trace_id]
            trace.finish()
            
            if self._enabled:
                self._export_trace(trace)
            
            logger.info(f"Finished trace: {trace.name} (Duration: {trace.duration_ms:.2f}ms, Spans: {len(trace.spans)})")
    
    def _export_trace(self, trace: Trace) -> None:
        """Export trace to observability backend."""
        # In production, send to Jaeger, Zipkin, etc.
        # For now, just log detailed trace info
        if settings.DEBUG:
            logger.debug(f"Trace export: {trace}")
    
    def trace_operation(
        self,
        name: str,
        attributes: Dict[str, Any] = None,
    ) -> Callable:
        """
        Decorator to trace an operation.
        
        Args:
            name: Operation name
            attributes: Static attributes
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span = self.start_span(name, attributes=attributes)
                
                try:
                    result = await func(*args, **kwargs)
                    span.status = "ok"
                    return result
                except Exception as e:
                    span.set_error(e)
                    span.status = "error"
                    raise
                finally:
                    self.finish_span(span)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span = self.start_span(name, attributes=attributes)
                
                try:
                    result = func(*args, **kwargs)
                    span.status = "ok"
                    return result
                except Exception as e:
                    span.set_error(e)
                    span.status = "error"
                    raise
                finally:
                    self.finish_span(span)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def get_current_trace(self) -> Optional[Trace]:
        """Get the current active trace."""
        trace_id = current_trace_id.get()
        if trace_id:
            return self._traces.get(trace_id)
        return self._current_trace
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return self._current_span
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by its ID."""
        return self._traces.get(trace_id)


# Global tracer instance
tracer = Tracer()


def trace_operation(name: str, attributes: Dict[str, Any] = None):
    """Decorator for tracing operations."""
    return tracer.trace_operation(name, attributes)


def trace_transaction(name: str, attributes: Dict[str, Any] = None):
    """Decorator for tracing transactions (entire trace)."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace = tracer.start_trace(name, attributes)
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                if tracer.get_current_span():
                    tracer.get_current_span().set_error(e)
                raise
            finally:
                tracer.finish_trace(trace.trace_id)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            trace = tracer.start_trace(name, attributes)
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if tracer.get_current_span():
                    tracer.get_current_span().set_error(e)
                raise
            finally:
                tracer.finish_trace(trace.trace_id)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def get_current_span() -> Optional[Span]:
    """Get current active span."""
    return tracer.get_current_span()


def get_current_trace_id() -> Optional[str]:
    """Get current trace ID."""
    return current_trace_id.get()


def add_span_attribute(key: str, value: Any) -> None:
    """Add attribute to current span."""
    span = get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Dict[str, Any] = None) -> None:
    """Add event to current span."""
    span = get_current_span()
    if span:
        span.add_event(name, attributes)


__all__ = [
    "Tracer",
    "Trace",
    "Span",
    "tracer",
    "trace_operation",
    "trace_transaction",
    "get_current_span",
    "get_current_trace_id",
    "add_span_attribute",
    "add_span_event",
]