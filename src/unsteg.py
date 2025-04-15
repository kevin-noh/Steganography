'''
    TODO: If the number of quantized colors exceeds a certain threshold,
        make it try color quantization again with a smaller depth.
        This is required because if there are too many colors, it results in
        the brighter indexed colors which possibly get noticed.
        
    TODO: Currently, the hidden image is visible,
        if one adjusts the brightness/contrast of the image.
        
        To prevent this, we can try a few things that might works when it XORs the image:
    ┌────── 1. Evenly spread out the indexed image pixels into the target.
    │       2. Flatten the indexed image before XOR
    │       3. Scramble the indexed image in a REVERSIBLE manner before XOR
    │   
    └──>*UPDATE: The first method is now being used.
    
    TODO: If the target image is not in webp or jpeg format, convert it to webp/jpeg
        to reduce the result size, maybe?
        
        It is appending the original image at the end of the result image,
        so we don't need it separately to retrive the hidden image.
        And this makes the result be 2x bigger than the original now.
'''
import argparse
import math

from numpy import empty, bitwise_xor, asarray, uint8
from skimage.transform import resize
import cv2

input_img = None
target_img = None
w = 0
h = 0

'''
    A color palette of quantized colors at first,
    will also map the quantized colors to the corresponding indexed colors, later.
'''
decode_palette = dict()

def resize_input_image():
    global input_img
    
    print("before resize: ", input_img.shape, ", ", target_img.shape)
    if (input_img.shape[0] > target_img.shape[0]) or \
        (input_img.shape[1] > target_img.shape[1]):
        if target_img.shape[0] > target_img.shape[1]:
            percent = (target_img.shape[1] / float(input_img.shape[1]))
            other = int((float(input_img.shape[0]) * float(percent)))
            input_img = resize(input_img, (other, target_img.shape[1]), anti_aliasing=False, preserve_range=True)
        else:
            percent = (target_img.shape[0] / float(input_img.shape[0]))
            other = int((float(input_img.shape[1]) * float(percent)))
            input_img = resize(input_img, (target_img.shape[0], other), anti_aliasing=False, preserve_range=True)
        print("after resize: ", input_img.shape, ", ", target_img.shape)
        input_img = input_img.astype(uint8, copy=False)

# Read required metadata like color mappings, etc.
def read_decode_info(target_path):
    global input_img
    global w
    global h
    global decode_palette
    
    with open(target_path, "r+b") as img:
        f = img.read()
        b = bytearray(f)
        
        pointer = int.from_bytes(b[-4:], 'big')
        dims = b[pointer:pointer+8]
        h = int.from_bytes(dims[:4], 'big')
        w = int.from_bytes(dims[4:], 'big')
        pointer += 8
        print("W: ", w, ", H: ", h)
        dp_size = int.from_bytes(b[pointer:pointer+2], 'big')
        pointer += 2
        
        for i in range(dp_size):
            entry = bytearray(b[pointer:pointer+6])
            
            qr = entry[0]
            qg = entry[1]
            qb = entry[2]
            cr = entry[3]
            cg = entry[4]
            cb = entry[5]
            
            decode_palette[(cr, cg, cb)] = (qr, qg, qb)
            
            pointer += 6
            
        if pointer + 4 < len(b):
            orig_bytearray = b[pointer:-4]
            input_img = cv2.imdecode(asarray(orig_bytearray, dtype=uint8), cv2.IMREAD_COLOR)
            
        return w, h, decode_palette
    
'''
    TODO: Do not need to go through the image twice
        change it to one-pass and do XOR-ing and color mapping at the same time
'''
def unstegano_image(target_path):
    global input_img
    global target_img
    
    t_h = target_img.shape[0]
    t_w = target_img.shape[1]
    i_h = h
    i_w = w
    h_interval = math.floor(t_h / i_h)
    w_interval = math.floor(t_w / i_w)
    retrieved = empty((i_h, i_w, 3))
    
    for rindex in range(i_h):
        t_r = rindex * h_interval
        for cindex in range(i_w):
            t_c = cindex * w_interval
            
            # XOR-ed RGB
            rgb = (bitwise_xor(target_img[t_r][t_c][0], input_img[t_r][t_c][0]), \
            bitwise_xor(target_img[t_r][t_c][1], input_img[t_r][t_c][1]), \
            bitwise_xor(target_img[t_r][t_c][2], input_img[t_r][t_c][2]))
            # Recover quantized image from the indexed image
            rgb = decode_palette[rgb]
            retrieved[rindex][cindex] = list(rgb)
            
    # cv2.imwrite('./out/xor_out.png', retrieved)
    output_path = return_output_path(target_path) + 'decoded.png'
    cv2.imwrite(output_path, retrieved)

def return_output_path(target_path):
    i = target_path.rfind('\\')
    if i == -1:
        i = target_path.rfind('/')
    path = target_path[:i + 1]
    
    return path

'''
    Function below is for the scripts that use
    unsteg.py as its module
'''
def init_params(input_path, target_path):
    global input_img
    global target_img
    
    if not input_path is None:
        input_img = cv2.imread(input_path)
    target_img = cv2.imread(target_path)
    
    decode_palette.clear()
    read_decode_info(target_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform Median Cut Color Quantization on image.')
    parser.add_argument('-i', '--input', type=str, help='path to the image being stegano-ed or the original base image when unsteg')
    parser.add_argument('-t', '--target', type=str, help='path to the base image or the image where the hidden image is hiding')

    # Get the arguments
    args = parser.parse_args()

    # Get the values from the arguments
    input_path = args.input
    target_path = args.target
    
    # Read the images
    target_img = cv2.imread(target_path)
    read_decode_info(target_path)
    
    if input_img is None:
        input_img = cv2.imread(input_path)
        
    '''
        Check whether the image need to be resized
        If yes, make the input fit in the target
    '''
    resize_input_image()
    
    unstegano_image(target_path)
