import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

ROWS_PER_PAGE = 100

class TricksterXMLEditor:
    def __init__(self):
        self.tree = None
        self.root = None
        self.data = []  # List of (ET.Element, data_dict)
        self.headers = []
        self.file_path = None
        self.page = 0
        self.filtered_data = [] # List of references to items in self.data
        self.column_vars = {}
        self.visible_headers = []
        
        # For persistent widget grid
        self.header_label_widgets = []
        self.page_entry_widgets = [] # 2D list of tk.Entry
        self.page_entry_vars = []    # 2D list of tk.StringVar
        self.page_row_data_map = []  # Maps displayed row index to (ET.Element, data_dict)

        self._is_programmatic_update = False # Flag to prevent cell edit triggers during programmatic updates

        # UI Elements - initialized here for clarity, configured in setup_ui
        self.header_canvas = None
        self.header_scrollable_frame = None
        self.data_canvas = None # Renamed from self.canvas
        self.data_v_scrollbar = None # Renamed from self.scrollbar
        self.scrollable_frame = None # Frame inside data_canvas for data rows
        self.unified_h_scrollbar = None # For both header and data

        self.window = tk.Tk()
        self.window.title("Trickster XML Editor")
        self.setup_ui()
        self.window.mainloop()

    def setup_ui(self):
        self.menu = tk.Menu(self.window)
        self.window.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Open XML File", command=self.load_xml_file)
        self.menu.add_cascade(label="File", menu=file_menu)

        self.columns_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Columns", menu=self.columns_menu, state="disabled")

        self.search_frame = tk.Frame(self.window)
        self.search_frame.pack(fill="x", pady=5)

        tk.Label(self.search_frame, text="Search:").pack(side="left", padx=5)
        self.search_entry = tk.Entry(self.search_frame, width=40)
        self.search_entry.pack(side="left")

        tk.Label(self.search_frame, text="in").pack(side="left", padx=5)
        self.search_field = ttk.Combobox(self.search_frame, state="readonly", width=20)
        self.search_field.pack(side="left")

        tk.Button(self.search_frame, text="Search", command=self.apply_search).pack(side="left", padx=5)
        tk.Button(self.search_frame, text="Clear", command=self.clear_search).pack(side="left", padx=5)

        self.table_display_frame = tk.Frame(self.window)
        self.table_display_frame.pack(fill="both", expand=True)

        self.data_canvas = tk.Canvas(self.table_display_frame)
        self.data_v_scrollbar = tk.Scrollbar(self.table_display_frame, orient="vertical", command=self.data_canvas.yview)
        self.data_canvas.configure(yscrollcommand=self.data_v_scrollbar.set)
        
        self.scrollable_frame = tk.Frame(self.data_canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all"))
        )
        self.data_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.data_canvas.grid(row=0, column=0, sticky="nsew")
        self.data_v_scrollbar.grid(row=0, column=1, sticky="ns")

        self.table_display_frame.grid_rowconfigure(0, weight=1)
        self.table_display_frame.grid_columnconfigure(0, weight=1)
        
        # Nav frame and Save button need to be packed *after* table_display_frame is packed.
        # To ensure they are at the bottom. Let's use a bottom_frame for these.
        bottom_controls_frame = tk.Frame(self.window)
        bottom_controls_frame.pack(side="bottom", fill="x")

        self.nav_frame = tk.Frame(bottom_controls_frame)
        self.nav_frame.pack(fill="x") # Will be packed before save button in this frame
        
        self.page_label = tk.Label(self.nav_frame, text="Page 0 of 0")
        self.page_label.pack(side="left", padx=10)
        # Pack Next first to make it appear on the left of Previous (when using side="right")
        tk.Button(self.nav_frame, text="Next", command=self.next_page).pack(side="right", padx=(0,5))
        tk.Button(self.nav_frame, text="Previous", command=self.prev_page).pack(side="right")

        self.save_button = tk.Button(bottom_controls_frame, text="Save Edited XML", command=self.save_xml)
        self.save_button.pack(pady=5) # Below nav_frame

    def load_xml_file(self):
        path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if not path:
            return
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            rows = root.findall("ROW")
            if not rows:
                messagebox.showerror("Invalid File", "No <ROW> tags found.")
                return

            raw_data = []
            headers_set = set()
            for row_el in rows:
                row_data_dict = {}
                for child in row_el:
                    headers_set.add(child.tag)
                    row_data_dict[child.tag] = child.text or ""
                raw_data.append((row_el, row_data_dict))

            self.tree = tree
            self.root = root
            self.data = raw_data
            self.filtered_data = list(self.data) # Start with all data
            self.headers = sorted(list(headers_set))
            self.visible_headers = list(self.headers)
            self.file_path = path
            self.page = 0

            self.search_field['values'] = ['(All Fields)'] + self.headers
            self.search_field.current(0)
            
            self.column_vars.clear()
            self.columns_menu.delete(0, tk.END)
            if self.headers:
                self.menu.entryconfig("Columns", state="normal")
                for header in self.headers:
                    var = tk.BooleanVar(value=True)
                    self.column_vars[header] = var
                    self.columns_menu.add_checkbutton(
                        label=header, variable=var, command=self.on_column_visibility_change
                    )
            else:
                self.menu.entryconfig("Columns", state="disabled")

            self._build_display_grid() # This will also call _update_displayed_data

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XML: {e}")

    def _build_display_grid(self):
        # Clear previous header widgets
        for widget in self.header_scrollable_frame.winfo_children():
            widget.destroy()
        self.header_label_widgets.clear()

        # Clear previous data row widgets (from self.scrollable_frame inside data_canvas)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        # self.page_entry_widgets, self.page_entry_vars are rebuilt, so clearing them might be redundant if always fully repopulated
        self.page_entry_widgets.clear()
        self.page_entry_vars.clear()

        if not self.visible_headers:
            self.header_canvas.config(scrollregion=self.header_canvas.bbox("all"))
            self._update_displayed_data() 
            return

        # Build new headers in header_scrollable_frame
        for col_idx, header in enumerate(self.visible_headers):
            label = tk.Label(self.header_scrollable_frame, text=header, font=("Arial", 10, "bold"), borderwidth=1, relief="solid", width=20, anchor="w")
            label.grid(row=0, column=col_idx, sticky="ew")
            self.header_label_widgets.append(label)
        
        self.header_scrollable_frame.update_idletasks()
        self.header_canvas.config(scrollregion=self.header_canvas.bbox("all"))
        self.header_canvas.xview_moveto(0) # Reset horizontal scroll of headers

        # Build new data entry grid structure in self.scrollable_frame
        self.page_row_data_map = [None] * ROWS_PER_PAGE
        for r_idx in range(ROWS_PER_PAGE):
            row_widgets = []
            row_vars = []
            # Use len(self.visible_headers) for the number of columns
            for c_idx in range(len(self.visible_headers)):
                var = tk.StringVar()
                var.trace_add("write", lambda name, index, mode, ri=r_idx, ci=c_idx: self._handle_cell_edit(ri, ci))
                entry = tk.Entry(self.scrollable_frame, textvariable=var, width=20)
                entry.grid(row=r_idx, column=c_idx, sticky="ew") # Data rows start at r_idx 0 in their own frame
                row_widgets.append(entry)
                row_vars.append(var)
            self.page_entry_widgets.append(row_widgets)
            self.page_entry_vars.append(row_vars)
        
        self._update_displayed_data() # This will populate the grid and set data_canvas scrollregion

    def _update_displayed_data(self):
        if not self.filtered_data and not self.visible_headers: # No data and no headers
             self.page_label.config(text="Page 0 of 0")
             # Ensure canvas is cleared if it had old content before headers disappeared
             if not self.visible_headers:
                 for widget in self.scrollable_frame.winfo_children():
                    widget.destroy()
             return
        if not self.visible_headers: # Data exists but no columns selected
            self.page_label.config(text=f"Page {self.page + 1} of {max(1, (len(self.filtered_data) - 1) // ROWS_PER_PAGE + 1)} (No columns visible)")
            # Hide all entry widgets if headers are not visible
            for r_idx in range(ROWS_PER_PAGE):
                 for c_idx_entry in range(len(self.page_entry_widgets[r_idx]) if self.page_entry_widgets and r_idx < len(self.page_entry_widgets) else 0):
                    self.page_entry_widgets[r_idx][c_idx_entry].grid_remove()
            return

        start = self.page * ROWS_PER_PAGE
        end = min(start + ROWS_PER_PAGE, len(self.filtered_data))
        current_page_tuples = self.filtered_data[start:end]
        
        self.page_row_data_map = [None] * ROWS_PER_PAGE

        for r_idx_on_page in range(ROWS_PER_PAGE):
            if r_idx_on_page < len(current_page_tuples):
                el, data_dict = current_page_tuples[r_idx_on_page]
                self.page_row_data_map[r_idx_on_page] = (el, data_dict)
                for c_idx, header in enumerate(self.visible_headers):
                    var = self.page_entry_vars[r_idx_on_page][c_idx]
                    
                    self._is_programmatic_update = True
                    var.set(data_dict.get(header, ""))
                    self._is_programmatic_update = False

                    self.page_entry_widgets[r_idx_on_page][c_idx].grid() # Ensure visible
            else: # This row on page is empty
                self.page_row_data_map[r_idx_on_page] = None
                for c_idx in range(len(self.visible_headers)):
                    var = self.page_entry_vars[r_idx_on_page][c_idx]
                    
                    self._is_programmatic_update = True
                    var.set("")
                    self._is_programmatic_update = False
                    
                    self.page_entry_widgets[r_idx_on_page][c_idx].grid_remove() # Hide

        total_pages = max(1, (len(self.filtered_data) - 1) // ROWS_PER_PAGE + 1)
        self.page_label.config(text=f"Page {self.page + 1} of {total_pages}")
        self.scrollable_frame.update_idletasks() # Important for scrollregion update
        self.data_canvas.config(scrollregion=self.data_canvas.bbox("all"))
        self.data_canvas.xview_moveto(0) # Reset horizontal scroll of data rows

        # Also update header canvas scrollregion in case window was resized, though content unlikely to change here
        self.header_scrollable_frame.update_idletasks()
        self.header_canvas.config(scrollregion=self.header_canvas.bbox("all"))
        # self.header_canvas.xview_moveto(0) # Already done in _build_display_grid if headers changed

    def _handle_cell_edit(self, page_r_idx, page_c_idx):
        if self._is_programmatic_update: # Don't process edits made by the program itself
            return

        if self.page_row_data_map[page_r_idx] is None:
            return # Editing a blank part of the grid

        el, data_dict = self.page_row_data_map[page_r_idx]
        
        # Check if page_c_idx is valid for current visible_headers
        if page_c_idx >= len(self.visible_headers):
            # This can happen if columns were hidden after trace was set up
            # Or if var.set("") itself triggered a trace somehow before it was removed.
            # print(f"Warning: cell edit for invalid column index {page_c_idx}")
            return

        header = self.visible_headers[page_c_idx]
        
        # Check if the var actually exists for this cell, defensive
        if page_r_idx >= len(self.page_entry_vars) or page_c_idx >= len(self.page_entry_vars[page_r_idx]):
            # print(f"Warning: page_entry_vars out of bounds for {page_r_idx}, {page_c_idx}")
            return

        new_value = self.page_entry_vars[page_r_idx][page_c_idx].get()

        # Check if value actually changed to avoid recursion or unnecessary updates
        if data_dict.get(header, "") != new_value:
            data_dict[header] = new_value
            el.set("gui_edited", "true") # Mark element as modified by GUI

    def save_xml(self):
        if not self.tree:
            messagebox.showwarning("No Data", "No XML file loaded or data is empty.")
            return
        
        modified_count = 0
        for el, data_dict in self.data: # Iterate over the original self.data
            if el.get("gui_edited") == "true":
                modified_count +=1
                for tag, value_str in data_dict.items():
                    child = el.find(tag)
                    if child is None and value_str: # Create if doesn't exist and has content
                        child = ET.SubElement(el, tag)
                    if child is not None: # Update if exists (or was just created)
                        child.text = value_str
                el.set("processed", "true") # Original logic
                del el.attrib["gui_edited"] # Clean up temp flag
        
        if modified_count == 0:
            messagebox.showinfo("No Changes", "No changes detected to save.")
            return

        try:
            out_path = self.file_path.replace(".xml", "_edited.xml")
            self.tree.write(out_path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Saved", f"✅ Saved {modified_count} modified row(s) to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save XML: {e}")

    def apply_search(self):
        query = self.search_entry.get().lower().strip()
        field = self.search_field.get()

        if not query:
            self.filtered_data = list(self.data)
        elif field == "(All Fields)":
            self.filtered_data = [
                (el, d) for el, d in self.data
                if any(query in str(v or "").lower() for v in d.values())
            ]
        else:
            self.filtered_data = [
                (el, d) for el, d in self.data
                if query in str(d.get(field, "") or "").lower()
            ]
        self.page = 0
        self._update_displayed_data()

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.filtered_data = list(self.data)
        self.page = 0
        self._update_displayed_data()

    def on_column_visibility_change(self):
        self.visible_headers = [h for h in self.headers if self.column_vars.get(h) and self.column_vars[h].get()]
        self.page = 0
        self._build_display_grid() # Rebuild grid if column structure changes

    def next_page(self):
        max_page = (len(self.filtered_data) - 1) // ROWS_PER_PAGE
        if self.page < max_page:
            self.page += 1
            self._update_displayed_data()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._update_displayed_data()

    def _on_unified_horizontal_scroll(self, *args):
        "Called when the unified horizontal scrollbar is moved."
        self.header_canvas.xview(*args)
        self.data_canvas.xview(*args)

if __name__ == "__main__":
    TricksterXMLEditor()