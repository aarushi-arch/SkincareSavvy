path = r'c:\Users\Hp\Desktop\SkincareSavvy\face_analysis\static\face_analysis\css\styles.css'
with open(path,'rb') as f:
    data = f.read()
print('size', len(data))
print('first120', data[:120])
print('null count', data.count(b'\x00'))
print('end120', data[-120:])
