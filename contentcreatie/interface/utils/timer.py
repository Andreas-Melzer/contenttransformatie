import time
from typing import Optional, Literal
import streamlit as st # Only used for optional 'st' or 'sidebar' output

class Timer:
    """
    A general-purpose context manager to time code blocks.
    This is pure Python and can be used in any script.
    
    Usage:
        with Timer("My slow function"):
            # ... code to time ...
    """
    def __init__(self, 
                 name: str, 
                 output_location: Optional[Literal["st", "sidebar", "print"]] = "print"):
        """
        Initializes the timer.

        :param name: str, The name of the code block being timed.
        :param output_location: Optional[Literal["st", "sidebar", "print"]], 
            Where to print the output. Defaults to "print".
        """
        self.name = name
        self.output_location = output_location
        self.start_time = None

    def __enter__(self):
        """Starts the timer."""
        # time.perf_counter() is the most accurate clock for this purpose
        self.start_time = time.perf_counter() 
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stops the timer and prints the result."""
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        duration_str = f"[Timer] '{self.name}': {duration:.4f}s"
        
        if self.output_location == "st":
            st.caption(duration_str)
        elif self.output_location == "sidebar":
            st.sidebar.caption(duration_str)
        else:
            # Default behavior: print to console
            print(duration_str)