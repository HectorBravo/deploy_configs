"""
Version panel module for selecting deployment versions/tags.
"""

import customtkinter as ctk
from typing import Optional, Callable


class VersionPanel(ctk.CTkFrame):
    """Panel for selecting deployment versions from repository tags."""

    def __init__(self, master, on_version_changed: Optional[Callable] = None,
                 on_refresh: Optional[Callable] = None, **kwargs):
        """
        Initialize VersionPanel.

        Args:
            master: Parent widget.
            on_version_changed: Callback when selected version changes.
            on_refresh: Callback for manual refresh.
            **kwargs: Additional arguments passed to CTkFrame.
        """
        super().__init__(master, **kwargs)
        self._on_version_changed = on_version_changed
        self._on_refresh_callback = on_refresh
        self._current_tag: Optional[str] = None
        self._tags: list[str] = []

        # Main container
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header_frame.grid_columnconfigure(2, weight=1)

        self._header_label = ctk.CTkLabel(
            header_frame,
            text="Versions (Tags)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self._header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Version count label
        self._version_count_label = ctk.CTkLabel(
            header_frame,
            text="0 versions",
            font=ctk.CTkFont(size=12)
        )
        self._version_count_label.grid(row=0, column=1, padx=10, pady=10)

        # Refresh button
        self._refresh_btn = ctk.CTkButton(
            header_frame,
            text="Refresh Tags",
            command=self._on_refresh_clicked,
            width=130,
            height=30,
            corner_radius=5
        )
        self._refresh_btn.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # Last refresh label
        self._last_refresh_label = ctk.CTkLabel(
            header_frame,
            text="Last refresh: --",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self._last_refresh_label.grid(row=0, column=3, padx=10, pady=10, sticky="e")

        # Scrollable frame for tag list
        scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        scroll_frame.grid_columnconfigure(0, weight=1)

        self._tag_buttons: list[ctk.CTkRadioButton] = []
        self._tag_vars: list[ctk.StringVar] = []
        self._tag_frames: list[ctk.CTkFrame] = []

        # Load initial tags (empty until repo is connected)
        self._render_tags(scroll_frame)

    def set_tags(self, tags: list[str]):
        """
        Set the list of available tags.

        Args:
            tags: List of tag names.
        """
        self._tags = tags
        self._current_tag = None if tags else None
        self._render_tags(None)  # Will find scroll_frame internally
        self._version_count_label.configure(text=f"{len(tags)} versions")
        self._update_last_refresh()

    def _render_tags(self, parent_frame=None):
        """Render tag buttons in the scrollable frame."""
        # Clear existing
        for frame in self._tag_frames:
            frame.destroy()
        self._tag_frames.clear()
        self._tag_vars.clear()
        self._tag_buttons.clear()

        # Find scrollable frame
        if parent_frame is None:
            for child in self.winfo_children():
                if isinstance(child, ctk.CTkScrollableFrame):
                    parent_frame = child
                    break

        if parent_frame is None or not self._tags:
            if parent_frame:
                # Show empty message
                empty_label = ctk.CTkLabel(
                    parent_frame,
                    text="No tags available.\nConnect the repository to see versions.",
                    font=ctk.CTkFont(size=12),
                    anchor="c"
                )
                empty_label.pack(pady=50)
            return

        for i, tag in enumerate(self._tags):
            var = ctk.StringVar(value="" if self._current_tag != tag else tag)
            self._tag_vars.append(var)

            frame = ctk.CTkFrame(parent_frame, corner_radius=6)
            frame.pack(fill="x", padx=5, pady=2)
            frame.grid_columnconfigure(1, weight=1)

            radio = ctk.CTkRadioButton(
                frame,
                text=tag,
                variable=var,
                value=tag,
                command=self._on_tag_selected,
                font=ctk.CTkFont(size=12)
            )
            radio.pack(side="left", padx=(5, 10), pady=5)
            self._tag_buttons.append(radio)

            # Copy button
            copy_btn = ctk.CTkButton(
                frame,
                text="Copy",
                width=50,
                height=25,
                corner_radius=3,
                command=lambda t=tag: self._copy_tag(t)
            )
            copy_btn.pack(side="right", padx=2)

        self._tag_frames.append(frame)  # Track at least one

    def _on_tag_selected(self):
        """Handle tag selection."""
        for var in self._tag_vars:
            if var.get():
                self._current_tag = var.get()
                if self._on_version_changed:
                    self._on_version_changed(self._current_tag)
                break

    def _on_refresh_clicked(self):
        """Handle manual refresh click."""
        if self._on_refresh_callback:
            self._on_refresh_callback()

    def _copy_tag(self, tag: str):
        """Copy tag name to clipboard."""
        # Will be handled by the main window
        pass

    def get_selected_tag(self) -> Optional[str]:
        """Get the currently selected tag."""
        return self._current_tag

    def set_selected_tag(self, tag: str):
        """
        Set the selected tag programmatically.

        Args:
            tag: Tag name to select.
        """
        if tag in self._tags:
            self._current_tag = tag
            for var in self._tag_vars:
                var.set(tag if var.get() == tag else "")
            if self._on_version_changed:
                self._on_version_changed(tag)

    def _update_last_refresh(self):
        """Update the last refresh time label."""
        import time
        now = time.strftime("%H:%M:%S")
        self._last_refresh_label.configure(text=f"Last refresh: {now}")

    def set_repo_status(self, connected: bool):
        """
        Update UI based on repository connection status.

        Args:
            connected: Whether the repository is connected.
        """
        if connected:
            self._refresh_btn.configure(state="normal")
            self._header_label.configure(text="Versions (Tags)")
        else:
            self._refresh_btn.configure(state="disabled")
            self._header_label.configure(text="Versions (Disconnected)")
