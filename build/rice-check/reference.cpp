// Builds RT64 texture_hasher's Rice functions (copied unchanged, GPL) and prints their results on
// random inputs. g++ -O1 -std=c++17 -o reference reference.cpp && ./reference > ref.txt && node compare.js ref.txt
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <vector>
int main(){
    auto CalculateDXT = [&](uint32_t txl2words) {
        if (txl2words == 0) {
            return 1U;
        }
        else {
            return (2048 + txl2words - 1) / txl2words;
        }
    };
    auto Txl2Words = [&](uint32_t width, uint32_t size) {
        static uint32_t sizeBytes[4] = { 0, 1, 2, 4 };
        if (size == 0) {
            return std::max(1U, width / 16);
        }
        else {
            return std::max(1U, width * sizeBytes[size] / 8);
        }
    };
    auto ReverseDXT = [&](uint32_t val, uint32_t width, uint32_t size) {
        if (val == 0x800) {
            return 1;
        }

        int low = 2047 / val;
        if (CalculateDXT(low) > val) {
            low++;
        }

        int high = 2047 / (val - 1);
        if (low == high) {
            return low;
        }

        for (int i = low; i <= high; i++) {
            if (Txl2Words(width, size) == (uint32_t)i) {
                return i;
            }
        }

        return (low + high) / 2;
    };
    auto CalculateMaxCI8b = [&](const uint8_t *src, uint32_t width, uint32_t height, uint32_t rowStride) {
        uint8_t val = 0;
        for (uint32_t y = 0; y < height; ++y) {
            const uint8_t *buf = src + rowStride * y;
            for (uint32_t x = 0; x < width; ++x) {
                if (buf[x] > val) {
                    val = buf[x];
                }

                if (val == 0xFF) {
                    return uint8_t(0xFF);
                }
            }
        }

        return val;
    };
    auto CalculateMaxCI4b = [&](const uint8_t *src, uint32_t width, uint32_t height, uint32_t rowStride) {
        uint8_t val = 0;
        uint8_t val1, val2;
        width >>= 1;
        for (uint32_t y = 0; y < height; ++y) {
            const uint8_t *buf = src + rowStride * y;
            for (uint32_t x = 0; x < width; ++x) {
                val1 = buf[x] >> 4;
                val2 = buf[x] & 0xF;
                if (val1 > val) {
                    val = val1;
                }

                if (val2 > val) {
                    val = val2;
                }

                if (val == 0xF) {
                    return uint8_t(0xF);
                }
            }
        }

        return val;
    };
    auto RiceCRC32 = [](const uint8_t *src, int width, int height, int size, int rowStride) {
        uint32_t crc32Ret = 0;
        const uint32_t bytesPerLine = width << size >> 1;
        int y = height - 1;
        while (y >= 0) {
            uint32_t esi = 0;
            int x = bytesPerLine - 4;
            while (x >= 0) {
                esi = *(uint32_t *)(src + x);
                esi ^= x;

                crc32Ret = (crc32Ret << 4) + ((crc32Ret >> 28) & 15);
                crc32Ret += esi;
                x -= 4;
            }

            esi ^= y;
            crc32Ret += esi;
            src += rowStride;
            --y;
        }

        return crc32Ret;
    };
  // Deterministic random cases: print results for comparison.
  srand(12345);
  for (int c=0;c<3000;c++){
    int size=rand()%4; int width=1+rand()%64; int height=1+rand()%32; int stride=((width<<size>>1)+7)/8*8 + (rand()%3)*8;
    std::vector<uint8_t> buf(stride*height+64); for(auto&b:buf) b=rand()&255;
    printf("crc %d %d %d %d %u\n", size,width,height,stride, RiceCRC32(buf.data(),width,height,size,stride));
    printf("max4 %u max8 %u\n", CalculateMaxCI4b(buf.data(),width,height,stride), CalculateMaxCI8b(buf.data(),width,height,stride));
    for(size_t i=0;i<buf.size();i++) printf("%02x", buf[i]); printf("\n");
  }
  for (int v=2; v<=2048; v++) for (int s=0;s<4;s++) { int w=1+(v*7)%320; printf("rdxt %d %d %d %d\n", v,w,s, ReverseDXT(v,w,s)); }
  return 0;
}