"""
Face Recognition Service
Handles all face detection and recognition operations
"""

import cv2
import numpy as np
import face_recognition
from PIL import Image
import os
from typing import List, Tuple, Optional

class FaceRecognitionService:
    """Service for face detection and recognition operations"""
    
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in an image using OpenCV Haar cascades"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        return faces.tolist()
    
    def encode_face(self, image_path: str) -> Optional[np.ndarray]:
        """Encode a face from an image file"""
        try:
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) > 0:
                return face_encodings[0]
            return None
        except Exception as e:
            print(f"Error encoding face from {image_path}: {e}")
            return None
    
    def encode_face_from_array(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """Encode a face from an image array"""
        try:
            face_encodings = face_recognition.face_encodings(image_array)
            
            if len(face_encodings) > 0:
                return face_encodings[0]
            return None
        except Exception as e:
            print(f"Error encoding face from array: {e}")
            return None
    
    def recognize_face(self, face_encoding: np.ndarray, tolerance: float = 0.6) -> Optional[str]:
        """Recognize a face from known encodings"""
        if len(self.known_face_encodings) == 0:
            return None
        
        matches = face_recognition.compare_faces(
            self.known_face_encodings, 
            face_encoding, 
            tolerance=tolerance
        )
        
        face_distances = face_recognition.face_distance(
            self.known_face_encodings, 
            face_encoding
        )
        
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                return self.known_face_ids[best_match_index]
        
        return None
    
    def register_face(self, face_encoding: np.ndarray, face_id: str):
        """Register a new face encoding"""
        self.known_face_encodings.append(face_encoding)
        self.known_face_ids.append(face_id)
    
    def load_known_faces(self, faces_directory: str):
        """Load all known faces from a directory"""
        self.known_face_encodings = []
        self.known_face_ids = []
        
        if not os.path.exists(faces_directory):
            return
        
        for filename in os.listdir(faces_directory):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(faces_directory, filename)
                face_id = os.path.splitext(filename)[0]
                
                encoding = self.encode_face(file_path)
                if encoding is not None:
                    self.register_face(encoding, face_id)
    
    def capture_and_process_frame(self, camera_index: int = 0) -> Tuple[Optional[np.ndarray], List[Tuple[int, int, int, int]]]:
        """Capture frame from camera and detect faces"""
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return None, []
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return None, []
        
        faces = self.detect_faces(frame)
        return frame, faces
    
    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Preprocess image for face recognition"""
        # Convert PIL Image to numpy array
        image_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        return image_array
    
    def validate_face_image(self, image_path: str) -> bool:
        """Validate if image contains a detectable face"""
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            return len(face_locations) > 0
        except:
            return False
