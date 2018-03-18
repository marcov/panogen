/**
 * @file compareHist_Demo.cpp
 * @brief Sample code to use the function compareHist
 * @author OpenCV team
 */

#include "opencv2/imgcodecs.hpp"
#include "opencv2/highgui.hpp"
#include "opencv2/imgproc.hpp"
#include <iostream>

using namespace std;
using namespace cv;

const cv::HistCompMethods compare_method  = cv::HISTCMP_CORREL;

/**
 * @function main
 */
int main( int argc, char** argv )
{
    Mat src_base, hsv_base;
    Mat src_test1, hsv_test1;

    /// Load three images with different environment settings
    if( argc < 3 )
    {
        printf("** Error. Usage: comparator <image0> <image1> \n");
        return -1;
    }

    src_base = imread( argv[1], IMREAD_COLOR );
    src_test1 = imread( argv[2], IMREAD_COLOR );

    if(src_base.empty() || src_test1.empty())
    {
      cout << "Can't read one of the images" << endl;
      return -1;
    }

    /// Convert to HSV
    cvtColor( src_base, hsv_base, COLOR_BGR2HSV );
    cvtColor( src_test1, hsv_test1, COLOR_BGR2HSV );


    /// Using 50 bins for hue and 60 for saturation
    int h_bins = 50; int s_bins = 60;
    int histSize[] = { h_bins, s_bins };

    // hue varies from 0 to 179, saturation from 0 to 255
    float h_ranges[] = { 0, 180 };
    float s_ranges[] = { 0, 256 };

    const float* ranges[] = { h_ranges, s_ranges };

    // Use the o-th and 1-st channels
    int channels[] = { 0, 1 };


    /// Histograms
    MatND hist_base;
    MatND hist_test1;

    /// Calculate the histograms for the HSV images
    calcHist( &hsv_base, 1, channels, Mat(), hist_base, 2, histSize, ranges, true, false );
    normalize( hist_base, hist_base, 0, 1, NORM_MINMAX, -1, Mat() );

    calcHist( &hsv_test1, 1, channels, Mat(), hist_test1, 2, histSize, ranges, true, false );
    normalize( hist_test1, hist_test1, 0, 1, NORM_MINMAX, -1, Mat() );

    /// Apply the histogram comparison methods
    //double base_base  = compareHist(hist_base, hist_base, compare_method );
    double base_test1 = compareHist(hist_base, hist_test1, compare_method );

    //printf(" Compare method = %u - value =  %f \n", compare_method, base_test1);

    cout << base_test1 << endl;

    return 0;
}
