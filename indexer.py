#!python3.12
"""
watch_knowledge.py - Monitors the knowledge base directory and automatically runs indexing 
when files are added or modified.

This script uses the watchdog library to monitor file system events and trigger
the indexing process only for relevant changes.
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
except ImportError:
    print("Required package 'watchdog' not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "watchdog"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

# Default settings
DEFAULT_KNOWLEDGE_DIR = "knowledge_base"
DEFAULT_INDEX_NAME = "seo_index"
DEFAULT_COOLDOWN = 5  # seconds to wait after last change before indexing

class KnowledgeBaseHandler(FileSystemEventHandler):
    """Handler for file system events in the knowledge base directory."""
    
    def __init__(self, knowledge_dir: str, index_name: str, tags: Optional[List[str]] = None, 
                 cooldown: int = DEFAULT_COOLDOWN):
        self.knowledge_dir = knowledge_dir
        self.index_name = index_name
        self.tags = tags
        self.cooldown = cooldown
        self.last_event_time = 0
        self.pending_index = False
        self.supported_extensions = ['.txt', '.md', '.html', '.json', '.csv']
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and self._is_relevant_file(event.src_path):
            self._schedule_indexing()
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and self._is_relevant_file(event.src_path):
            self._schedule_indexing()
    
    def _is_relevant_file(self, file_path: str) -> bool:
        """Check if the file is relevant for indexing"""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.supported_extensions
    
    def _schedule_indexing(self):
        """Schedule indexing after cooldown period"""
        self.last_event_time = time.time()
        self.pending_index = True
    
    def check_if_should_index(self) -> bool:
        """Check if enough time has passed since the last event to trigger indexing"""
        if not self.pending_index:
            return False
        
        time_since_last_event = time.time() - self.last_event_time
        if time_since_last_event >= self.cooldown:
            self.pending_index = False
            return True
        return False
    
    def run_indexing(self):
        """Run the indexing process"""
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running indexing process...")
        
        # Build the command
        cmd = [sys.executable, "index_knowledge.py", 
               "--knowledge", self.knowledge_dir, 
               "--index", self.index_name]
        
        # Add tags if specified
        if self.tags:
            cmd.extend(["--tags"] + self.tags)
        
        # Run the indexing script
        try:
            subprocess.run(cmd, check=True)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Indexing completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Indexing failed: {e}")

def main():
    """Main function to run the directory watcher."""
    parser = argparse.ArgumentParser(description="Watch knowledge base directory and run indexing when files change")
    parser.add_argument("--knowledge", default=DEFAULT_KNOWLEDGE_DIR,
                        help=f"Directory containing knowledge base documents (default: {DEFAULT_KNOWLEDGE_DIR})")
    parser.add_argument("--index", default=DEFAULT_INDEX_NAME,
                        help=f"Name of the vector index to update (default: {DEFAULT_INDEX_NAME})")
    parser.add_argument("--tags", nargs='+', 
                        help="Only include documents with these tags in the YAML front matter")
    parser.add_argument("--cooldown", type=int, default=DEFAULT_COOLDOWN,
                        help=f"Seconds to wait after last change before indexing (default: {DEFAULT_COOLDOWN})")
    
    args = parser.parse_args()
    
    # Create knowledge directory if it doesn't exist
    Path(args.knowledge).mkdir(exist_ok=True)
    
    # Set up the event handler and observer
    event_handler = KnowledgeBaseHandler(
        knowledge_dir=args.knowledge,
        index_name=args.index,
        tags=args.tags,
        cooldown=args.cooldown
    )
    
    observer = Observer()
    observer.schedule(event_handler, args.knowledge, recursive=True)
    observer.start()
    
    print(f"Watching directory: {os.path.abspath(args.knowledge)}")
    print(f"Index name: {args.index}")
    if args.tags:
        print(f"Filtering for tags: {', '.join(args.tags)}")
    print("Press Ctrl+C to stop watching...")
    
    try:
        # Initial indexing when starting the watcher
        event_handler.run_indexing()
        
        # Main loop
        while True:
            # Check if we should run indexing
            if event_handler.check_if_should_index():
                event_handler.run_indexing()
            
            # Sleep to avoid high CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping directory watcher...")
        observer.stop()
    
    observer.join()
    return 0

if __name__ == "__main__":
    sys.exit(main())
