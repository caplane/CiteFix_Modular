@staticmethod
    def _chicago_interview(data):
        # Target: Joh Brown, Interview by author. May 7, 1918.
        
        parts = []
        
        # 1. Interviewee (Joh Brown)
        interviewee = data.get('interviewee', '')
        if interviewee:
            # Check for "Last, First" and flip it to "First Last" if needed
            if ',' in interviewee:
                names = interviewee.split(',')
                interviewee = f"{names[1].strip()} {names[0].strip()}"
            parts.append(interviewee)
        
        # 2. Descriptor (The Logic Fix)
        interviewer = data.get('interviewer', '')
        if interviewer:
            descriptor = f"Interview by {interviewer}"
        else:
            descriptor = "Interview by author"  # <--- Forces this text when no name is found
            
        # Join Name and Descriptor with a COMMA
        result = f"{parts[0]}, {descriptor}" if parts else descriptor
        
        # 3. Date (Add with a PERIOD)
        if data.get('date'):
            result += f". {data['date']}"
            
        return result + "."
