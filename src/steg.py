'''
    todo: if the number of quantized colors exceeds a certain threshold,
        make it try color quantization again with a smaller depth.
        this is required because if there are too many colors, it results in
        the brighter indexed colors which possibly get noticed.
        
    todo: currently, the hidden image is visible,
        if one adjusts the brightness/contrast of the image.
        
        to prevent this, we can try a few things that might works when it xors the image:
    ┌────── 1. evenly spread out the indexed image pixels into the target.
    │       2. flatten the indexed image before xor
    │       3. scramble the indexed image in a reversible manner before xor
    │   
    └──>*update: the first method is now being used.
    
    todo: if the target image is not in webp or jpeg format, convert it to webp/jpeg
        to reduce the result size, maybe?
        
        it is appending the original image at the end of the result image,
        so we don't need it separately to retrive the hidden image.
        and this makes the result be 2x bigger than the original now.
'''
import argparse
from math import floor

from numpy import uint8, bitwise_xor, max, min, mean, array
from skimage.transform import resize
import cv2

input_img = None
target_img = None
save = False

'''
    a color palette of quantized colors at first,
    will also map the quantized colors to the corresponding indexed colors, later.
'''
quantized_palette = dict()

def resize_input_image():
    global input_img
    
    print("before resize: ", input_img.shape, ", ", target_img.shape)
    if (input_img.shape[0] > target_img.shape[0]) or \
        (input_img.shape[1] > target_img.shape[1]):
        if target_img.shape[0] > target_img.shape[1]:
            percent = (target_img.shape[1] / float(input_img.shape[1]))
            other = int((float(input_img.shape[0]) * float(percent)))
            input_img = resize(input_img, (other, target_img.shape[1]), anti_aliasing=false, preserve_range=true)
        else:
            percent = (target_img.shape[0] / float(input_img.shape[0]))
            other = int((float(input_img.shape[1]) * float(percent)))
            input_img = resize(input_img, (target_img.shape[0], other), anti_aliasing=false, preserve_range=true)
        print("after resize: ", input_img.shape, ", ", target_img.shape)
        input_img = input_img.astype(uint8, copy=false)

'''
    swap the keys/values of quantized_palette and
    convert it into a byte array
    
    the first two bytes are the length of palette
'''
def write_decode_palette():
    b = bytearray()
    b += len(quantized_palette).to_bytes(2, byteorder='big')
    
    for c in quantized_palette:
        qr, qg, qb = c
        cr, cg, cb = quantized_palette[c]
        
        b += int(qr).to_bytes(1, byteorder='big')
        b += int(qg).to_bytes(1, byteorder='big')
        b += int(qb).to_bytes(1, byteorder='big')
        b += int(cr).to_bytes(1, byteorder='big')
        b += int(cg).to_bytes(1, byteorder='big')
        b += int(cb).to_bytes(1, byteorder='big')
    
    return b

# xor each pixels of two given images
def xor_img(input_img, target_img):
    t_h = target_img.shape[0]
    t_w = target_img.shape[1]
    i_h = input_img.shape[0]
    i_w = input_img.shape[1]
    h_interval = floor(t_h / i_h)
    w_interval = floor(t_w / i_w)
    
    for rindex in range(i_h):
        t_r = rindex * h_interval
        for cindex in range(i_w):
            t_c = cindex * w_interval
            target_img[t_r][t_c][0] = \
            bitwise_xor(target_img[t_r][t_c][0], input_img[rindex][cindex][0])
            target_img[t_r][t_c][1] = \
            bitwise_xor(target_img[t_r][t_c][1], input_img[rindex][cindex][1])
            target_img[t_r][t_c][2] = \
            bitwise_xor(target_img[t_r][t_c][2], input_img[rindex][cindex][2])
            
    return target_img
    
# return n (num_codes) codes
def return_index(num_code, thrsh):
    codes = []
    
    i = 0; j = 0; k = -1;
    for n in range(num_code):
        k += 1
        if k >= thrsh:
            k = 0
            j += 1
            if j >= thrsh:
                j = 0
                i += 1
                if i >= thrsh:
                    thrsh += 1
        codes.append((i, j, k))
    
    return codes

# quantized color == the center of the boxes    
def median_cut_quantize(img, img_arr, depth):
    global input_img
    # when it reaches the end, color quantize
    r_average = floor(mean(img_arr[:, 0]))
    g_average = floor(mean(img_arr[:, 1]))
    b_average = floor(mean(img_arr[:, 2]))
    
    rgb = (r_average, g_average, b_average)

    for data in img_arr:
        input_img[data[3]][data[4]] = list(rgb)

# recursive, median-cut color quantization
def split_into_buckets(img, img_arr, depth):
    if len(img_arr) == 0:
        return

    if depth <= 0:
        median_cut_quantize(img, img_arr, depth)
        return

    r_range = max(img_arr[:, 0]) - min(img_arr[:, 0])
    g_range = max(img_arr[:, 1]) - min(img_arr[:, 1])
    b_range = max(img_arr[:, 2]) - min(img_arr[:, 2])

    space_with_highest_range = 0

    if g_range >= r_range and g_range >= b_range:
        space_with_highest_range = 1
    elif b_range >= r_range and b_range >= g_range:
        space_with_highest_range = 2
    elif r_range >= b_range and r_range >= g_range:
        space_with_highest_range = 0

    '''
        sort the image pixels by color space with highest range
        and find the median and divide the array.
    '''
    img_arr = img_arr[img_arr[:, space_with_highest_range].argsort()]
    median_index = int((len(img_arr) + 1) / 2)

    # split the array into two blocks
    split_into_buckets(img, img_arr[0:median_index], depth - 1)
    split_into_buckets(img, img_arr[median_index:], depth - 1)

def stegano_image(target_path, output_path):
    global input_img
    global target_img
    global quantized_palette
    
    # flat out the input image to perform median-cut color quantization on the input
    flattened_img_array = []
    flattened_orig = []
    for rindex, rows in enumerate(input_img):
        for cindex, color in enumerate(rows):
            flattened_img_array.append([color[0], color[1], color[2], rindex, cindex])
            flattened_orig.append(color[0])
            flattened_orig.append(color[1])
            flattened_orig.append(color[2])
    
    flattened_img_array = array(flattened_img_array)
    
    split_into_buckets(input_img, flattened_img_array, 8)
    
    # cv2.imwrite('./out/before_index.png', input_img)
    
    '''
        with the quantized image, make a color palette and 
        count each color's appearance
    '''
    for rindex, rows in enumerate(input_img):
        for cindex, color in enumerate(rows):
            rgb = (color[0], color[1], color[2])
            if not rgb in quantized_palette:
                quantized_palette[rgb] = 1
            else:
                quantized_palette[rgb] += 1
    
    # sort the colors by the appearance frequency in descending order
    quantized_palette = sorted(quantized_palette.items(), key=lambda item: item[1], reverse=True)
    
    '''
        encode the colors into indexed colors
        the more frequently appeared, the closer to black (#000000)
    '''
    cube_root = floor(len(quantized_palette) ** (1. / 3))
    indexed_colors = return_index(len(quantized_palette), cube_root)
    for idx, (c, cc) in enumerate(quantized_palette):
        quantized_palette[idx] = (c, indexed_colors[idx])
    
    quantized_palette = dict(quantized_palette)
    
    # update the input image with indexed colors
    for rindex, rows in enumerate(input_img):
        for cindex, color in enumerate(rows):
            rgb = (color[0], color[1], color[2])
            rgb = quantized_palette[rgb]
            input_img[rindex][cindex] = list(rgb)
    
    print("reduced and encoded into ", len(quantized_palette), "colors")
    # cv2.imwrite('./out/after_index.png', input_img)
    
    # input image xor target image
    steged = xor_img(input_img, target_img)
    if output_path.endswith(".png"):
        cv2.imwrite(output_path, steged, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    else:
        cv2.imwrite(output_path, steged)
    
    '''
        write the input image dimension, # of colors, color mappings
        at the end of the output image
        
        todo?: maybe append the original target image here,
            so we do not need to have anything but just a single file
            to get the hidden image
    '''
    with open(output_path, "r+b") as img:
        f = img.read()
        img.seek(0)
        b = bytearray(f)
        
        eof_offset = len(b)
        
        b += input_img.shape[0].to_bytes(4, byteorder='big')
        b += input_img.shape[1].to_bytes(4, byteorder='big')
        
        b += write_decode_palette()
        
        if save:
            flattened_orig = []
            with open(target_path, "rb") as orig:
                of = orig.read()
                orig_b = bytearray(of)
                b += orig_b
        
        b += eof_offset.to_bytes(4, byteorder='big')
        
        img.write(b)
        img.truncate()

def return_output_path(target_path):
    ei = target_path.rfind('.')
    savename = target_path[:ei]
    ext = target_path[ei:]
    if target_path.endswith(".jpg") or target_path.endswith(".jpeg"):
        ext = ".webp"
    output_path = savename + "_" + ext
    
    return output_path
    
'''
    function below is for the scripts that use
    steg.py as its module
'''
def init_params(input_path, target_path, save_flag):
    global input_img
    global target_img
    global save
    input_img = cv2.imread(input_path)
    target_img = cv2.imread(target_path)
    quantized_palette.clear()
    save = save_flag


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform Median Cut Color Quantization on image.')
    parser.add_argument('-i', '--input', type=str, help='path to the image being stegano-ed or the original base image when unsteg')
    parser.add_argument('-t', '--target', type=str, help='path to the base image or the image where the hidden image is hiding')
    parser.add_argument('-s', '--save', type=int, default=1, help='0 for default, 1 for saving original image within the result')

    # Get the arguments
    args = parser.parse_args()

    # Get the values from the arguments
    input_path = args.input
    target_path = args.target
    output_path = return_output_path(target_path)
    
    # Read the images
    input_img = cv2.imread(input_path)
    target_img = cv2.imread(target_path)
    
    '''
        Check whether the image need to be resized
        If yes, make the input fit in the target
    '''
    resize_input_image()
    
    save = args.save
    
    stegano_image(target_path, output_path)
