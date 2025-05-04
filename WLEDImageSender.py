import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
import requests
import json
from PIL import Image, ImageTk
import numpy as np

class WLEDPixelControl:
    def __init__(self, root):
        self.root = root
        self.root.title("WLED Pixel Controller")
        
        # IP Address input
        self.ip_frame = ttk.LabelFrame(root, text="WLED Connection", padding="5")
        self.ip_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.ip_label = ttk.Label(self.ip_frame, text="IP Address:")
        self.ip_label.grid(row=0, column=0, padx=5, pady=5)
        
        self.ip_entry = ttk.Entry(self.ip_frame)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        self.ip_entry.insert(0, "192.168.5.4")

        # Matrix configuration
        self.matrix_frame = ttk.LabelFrame(root, text="Matrix Configuration", padding="5")
        self.matrix_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.matrix_width_label = ttk.Label(self.matrix_frame, text="Width:")
        self.matrix_width_label.grid(row=0, column=0, padx=5, pady=5)
        self.matrix_width_entry = ttk.Entry(self.matrix_frame, width=10)
        self.matrix_width_entry.grid(row=0, column=1, padx=5, pady=5)
        self.matrix_width_entry.insert(0, "16")
        
        self.matrix_height_label = ttk.Label(self.matrix_frame, text="Height:")
        self.matrix_height_label.grid(row=0, column=2, padx=5, pady=5)
        self.matrix_height_entry = ttk.Entry(self.matrix_frame, width=10)
        self.matrix_height_entry.grid(row=0, column=3, padx=5, pady=5)
        self.matrix_height_entry.insert(0, "16")
        
        # Image control frame
        self.image_frame = ttk.LabelFrame(root, text="Image Control", padding="5")
        self.image_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        
        self.load_image_button = ttk.Button(self.image_frame, text="Load Image", command=self.load_image)
        self.load_image_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.generate_button = ttk.Button(self.image_frame, text="Generate Matrix", command=self.generate_matrix)
        self.generate_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas_frame = ttk.Frame(root)
        self.canvas_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        
        self.canvas = tk.Canvas(self.canvas_frame, width=400, height=400, bg='white')
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        # Original pixel control frame (now below image)
        self.pixel_frame = ttk.LabelFrame(root, text="Single Pixel Control", padding="5")
        self.pixel_frame.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        
        self.pixel_label = ttk.Label(self.pixel_frame, text="Pixel Number:")
        self.pixel_label.grid(row=0, column=0, padx=5, pady=5)
        
        self.pixel_entry = ttk.Entry(self.pixel_frame, width=10)
        self.pixel_entry.grid(row=0, column=1, padx=5, pady=5)
        self.pixel_entry.insert(0, "0")
        
        self.color_button = ttk.Button(self.pixel_frame, text="Select Color", command=self.choose_color)
        self.color_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.set_button = ttk.Button(self.pixel_frame, text="Set Pixel", command=self.set_pixel)
        self.set_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Status label at the bottom
        self.status_label = ttk.Label(root, text="")
        self.status_label.grid(row=5, column=0, padx=5, pady=5)
        
        # Initialize variables
        self.current_color = (255, 0, 0)  # Default color (red)
        self.image = None
        self.photo = None
        self.selection_rect = None
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.drag_mode = None
        self.fixed_corner = None
        self.scale_corner = None
        
        # Bind mouse events for selection rectangle
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Make the window resizable
        root.rowconfigure(3, weight=1)
        root.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

    def get_matrix_ratio(self):
        width = int(self.matrix_width_entry.get())
        height = int(self.matrix_height_entry.get())
        return width / height

    def get_nearest_corner(self, x, y, rect_coords):
        """Get the nearest corner of the rectangle to the given point"""
        x1, y1, x2, y2 = rect_coords
        corners = [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]
        return min(corners, key=lambda c: ((c[0] - x) ** 2 + (c[1] - y) ** 2) ** 0.5)

    def on_press(self, event):
        if not self.selection_rect:
            return
            
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Get current rectangle coordinates
        rect_coords = self.canvas.coords(self.selection_rect)
        x1, y1, x2, y2 = rect_coords
        
        # Check if click is inside the rectangle
        if (x1 <= self.start_x <= x2 and y1 <= self.start_y <= y2):
            # Store offset for moving
            self.drag_mode = "move"
            self.drag_offset = (self.start_x - x1, self.start_y - y1)
        else:
            # Store nearest corner for scaling
            self.drag_mode = "scale"
            self.fixed_corner = self.get_nearest_corner(self.start_x, self.start_y, rect_coords)
            # Get the opposite corner which will be fixed during scaling
            x1, y1, x2, y2 = rect_coords
            if self.fixed_corner == (x1, y1):
                self.scale_corner = (x2, y2)
            elif self.fixed_corner == (x2, y2):
                self.scale_corner = (x1, y1)
            elif self.fixed_corner == (x1, y2):
                self.scale_corner = (x2, y1)
            else:  # (x2, y1)
                self.scale_corner = (x1, y2)

    def on_drag(self, event):
        if not self.image or not self.selection_rect:
            return
            
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # Get matrix aspect ratio
        aspect_ratio = self.get_matrix_ratio()
        
        if self.drag_mode == "move":
            # Get current rectangle coordinates
            x1, y1, x2, y2 = self.canvas.coords(self.selection_rect)
            rect_width = x2 - x1
            rect_height = y2 - y1
            
            # Moving the rectangle
            dx = cur_x - self.start_x
            dy = cur_y - self.start_y
            
            # Calculate new position
            new_x1 = x1 + dx
            new_y1 = y1 + dy
            new_x2 = new_x1 + rect_width
            new_y2 = new_y1 + rect_height
            
            # Keep rectangle within image bounds
            if self.photo:
                if new_x1 < 0:
                    new_x1 = 0
                    new_x2 = rect_width
                if new_y1 < 0:
                    new_y1 = 0
                    new_y2 = rect_height
                if new_x2 > self.photo.width():
                    new_x2 = self.photo.width()
                    new_x1 = new_x2 - rect_width
                if new_y2 > self.photo.height():
                    new_y2 = self.photo.height()
                    new_y1 = new_y2 - rect_height
            
            self.canvas.coords(self.selection_rect, new_x1, new_y1, new_x2, new_y2)
            self.start_x = cur_x
            self.start_y = cur_y
            
        elif self.drag_mode == "scale":
            # Calculate the new width based on the distance from the fixed corner
            dx = cur_x - self.scale_corner[0]
            dy = cur_y - self.scale_corner[1]
            
            # Use the larger dimension to determine scale while maintaining aspect ratio
            if abs(dx) / aspect_ratio > abs(dy):
                width = abs(dx)
                height = width / aspect_ratio
            else:
                height = abs(dy)
                width = height * aspect_ratio
                
            # Ensure minimum size
            min_size = 20
            width = max(width, min_size)
            height = width / aspect_ratio
            
            # Calculate new coordinates based on which corner is fixed
            x1, y1, x2, y2 = self.canvas.coords(self.selection_rect)
            if self.scale_corner == (x1, y1):
                new_coords = [x1, y1, x1 + width, y1 + height]
            elif self.scale_corner == (x2, y2):
                new_coords = [x2 - width, y2 - height, x2, y2]
            elif self.scale_corner == (x1, y2):
                new_coords = [x1, y2 - height, x1 + width, y2]
            else:  # (x2, y1)
                new_coords = [x2 - width, y1, x2, y1 + height]
            
            # Keep rectangle within image bounds
            if self.photo:
                if new_coords[0] < 0:
                    new_coords[0] = 0
                    new_coords[2] = width
                if new_coords[1] < 0:
                    new_coords[1] = 0
                    new_coords[3] = height
                if new_coords[2] > self.photo.width():
                    new_coords[2] = self.photo.width()
                    new_coords[0] = new_coords[2] - width
                if new_coords[3] > self.photo.height():
                    new_coords[3] = self.photo.height()
                    new_coords[1] = new_coords[3] - height
            
            self.canvas.coords(self.selection_rect, *new_coords)

    def on_release(self, event):
        self.drag_mode = None
        self.fixed_corner = None
        self.scale_corner = None

    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            try:
                self.image = Image.open(file_path)
                # Resize image to fit canvas while maintaining aspect ratio
                display_size = (400, 400)
                self.image.thumbnail(display_size, Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(self.image)
                
                # Clear canvas and display image
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
                self.canvas.config(scrollregion=self.canvas.bbox("all"))
                
                # Create initial selection rectangle with proper aspect ratio
                aspect_ratio = self.get_matrix_ratio()
                rect_width = min(100, self.image.width)
                rect_height = rect_width / aspect_ratio
                
                # Center the initial rectangle
                x1 = (self.image.width - rect_width) / 2
                y1 = (self.image.height - rect_height) / 2
                
                self.selection_rect = self.canvas.create_rectangle(
                    x1, y1, x1 + rect_width, y1 + rect_height,
                    outline='red', width=2
                )
                
            except Exception as e:
                self.status_label.config(text=f"Error loading image: {str(e)}")

    def generate_matrix(self):
        if not self.image or not self.selection_rect:
            self.status_label.config(text="Please load an image and select an area first")
            return
            
        try:
            # Get selection rectangle coordinates
            bbox = self.canvas.coords(self.selection_rect)
            x1, y1, x2, y2 = map(int, bbox)
            
            # Get matrix dimensions
            matrix_width = int(self.matrix_width_entry.get())
            matrix_height = int(self.matrix_height_entry.get())
            
            # Calculate selected region in original image coordinates
            selected_region = self.image.crop((x1, y1, x2, y2))
            
            # Resize to matrix dimensions
            matrix_image = selected_region.resize((matrix_width, matrix_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB array
            rgb_array = list(matrix_image.convert('RGB').getdata())
            
            # Create pixel array for WLED
            pixel_array = [[r, g, b] for r, g, b in rgb_array]
            
            # Create segment data
            segment_data = {
                "on": True,
                "bri": 255,
                "seg": [
                    {
                        "id": 0,
                        "i": pixel_array
                    }
                ]
            }
            
            # Send to WLED
            ip = self.ip_entry.get()
            url = f"http://{ip}/json/state"
            response = requests.post(url, json=segment_data)
            
            if response.status_code == 200:
                self.status_label.config(text="Matrix data sent successfully")
            else:
                self.status_label.config(text=f"Error sending data: {response.status_code}")
                
        except Exception as e:
            self.status_label.config(text=f"Error generating matrix: {str(e)}")

    def choose_color(self):
        color = colorchooser.askcolor(title="Choose Color")
        if color[0]:  # If color was selected
            self.current_color = tuple(map(int, color[0]))
            
    def set_pixel(self):
        try:
            ip = self.ip_entry.get()
            pixel_num = int(self.pixel_entry.get())
            
            # Create array of blank pixels up to the target pixel
            pixel_array = [[0, 0, 0]] * pixel_num  # Create blank pixels
            # Add the colored pixel at the specified position
            pixel_array.append([self.current_color[0], self.current_color[1], self.current_color[2]])
            
            # Create segment data
            segment_data = {
                "on": True,
                "bri": 255,
                "seg": [
                    {
                        "id": 0,
                        "i": pixel_array
                    }
                ]
            }
            
            # Show the request body first
            self.status_label.config(
                text=f"Sending request:\n{json.dumps(segment_data, indent=2)}"
            )
            self.root.update()  # Force update the GUI to show the request
            
            # Send request to WLED
            url = f"http://{ip}/json/state"
            response = requests.post(url, json=segment_data)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    self.status_label.config(
                        text=f"Request sent:\n{json.dumps(segment_data, indent=2)}\n\n" +
                             f"Response:\n{json.dumps(response_data, indent=2)}"
                    )
                except json.JSONDecodeError:
                    self.status_label.config(
                        text=f"Request sent:\n{json.dumps(segment_data, indent=2)}\n\n" +
                             f"Response: {response.text[:100]}"
                    )
            else:
                self.status_label.config(
                    text=f"Request sent:\n{json.dumps(segment_data, indent=2)}\n\n" +
                         f"Error {response.status_code}: {response.text[:100]}"
                )
                
        except requests.RequestException as e:
            self.status_label.config(text=f"Network Error: {str(e)}")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WLEDPixelControl(root)
    root.mainloop()