"""Session-local last-good numerical values during short cross-process contention."""
from pathlib import Path
import streamlit as st
from .core import Library
from .locking import Busy


class UILibrary:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = st.session_state.setdefault('numerical_last_good', {})
        self.initialized = False
        try:
            self.library = Library(root)
            self.initialized = True
        except Busy:
            st.warning('Numerical update in progress. Last rendered session data are retained; retry shortly.')
            self.library = Library.__new__(Library)
            self.library.root = self.root

    def __getattr__(self, name):
        function = getattr(self.library, name)
        def call(*args, **kwargs):
            key = repr((str(self.root), name, args, kwargs))
            try:
                if not self.initialized:
                    raise Busy('Constructor initialization deferred')
                result = function(*args, **kwargs)
                self.cache[key] = result
                return result
            except Busy:
                st.warning('Numerical update in progress. Showing last successful session values where available; retry shortly.')
                if name == 'refresh':
                    return {'id': args[0], 'ok': False, 'deferred': True,
                            'error': 'Numerical update in progress; refresh deferred. Previous data remain available.'}
                if key in self.cache:
                    return self.cache[key]
                st.info('No session cache for this selection yet. Wait for the update and rerun.')
                st.stop()
        return call
