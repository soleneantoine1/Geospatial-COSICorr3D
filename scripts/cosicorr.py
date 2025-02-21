#!/usr/bin/env python3
"""
Move the Script to a Bin Directory: For the cosicorr command to be recognized globally,
move it to a directory that's in your system's PATH.
A common choice is /usr/local/bin/.
You may rename cosicorr.py to cosicorr for convenience.
>> sudo mv cosicorr.py /usr/local/bin/cosicorr
"""
import argparse
import glob
import itertools
import logging
import os
import numpy as np
from pathlib import Path

import geoCosiCorr3D.geoCore.constants as C
import geoCosiCorr3D.georoutines.geo_utils as geo_utils
from geoCosiCorr3D.geoCosiCorr3dLogger import geoCosiCorr3DLog
from geoCosiCorr3D.geoImageCorrelation.correlate import Correlate


def parse_list(value):
    return [float(item) for item in value.split(',')]


def ortho_func(args):
    from geoCosiCorr3D.geoOrthoResampling.geoOrtho import orthorectify

    if args.model_name == C.SATELLITE_MODELS.RFM:
        ortho_params = {"method": {"method_type": args.model_name,
                                   "metadata": args.rfm_fn,
                                   "corr_model": args.corr_model,
                                   },
                        "GSD": args.gsd,
                        "resampling_method": args.resampling_method}

        if os.path.isdir(args.o_ortho):
            o_ortho_path = os.path.join(
                args.o_ortho,
                f"ORTHO_{Path(args.input_img).stem}_{ortho_params['resampling_method']}_RFM_{ortho_params['GSD']}_GSD.tif")

        else:
            o_ortho_path = args.o_ortho
        geoCosiCorr3DLog('Orthorectification', os.path.dirname(o_ortho_path))

        orthorectify(args.input_img, o_ortho_path, ortho_params, None, args.dem, args.debug)

    if args.model_name == C.SATELLITE_MODELS.RSM:
        if args.model_name == C.SATELLITE_MODELS.RSM:
            ortho_params = {"method": {"method_type": args.model_name,
                                       "metadata": args.rsm_fn,
                                       "corr_model": args.corr_model,
                                       "sensor": args.sat_id,
                                       },
                            "GSD": args.gsd,
                            "resampling_method": args.resampling_method}

            if os.path.isdir(args.o_ortho):
                o_ortho_path = os.path.join(
                    args.o_ortho,
                    f"ORTHO_{Path(args.input_img).stem}_{ortho_params['resampling_method']}_RSM_{ortho_params['GSD']}_GSD.tif")

            else:
                o_ortho_path = args.o_ortho
            geoCosiCorr3DLog('Orthorectification', os.path.dirname(o_ortho_path))

            orthorectify(args.input_img, o_ortho_path, ortho_params, None, args.dem, args.refine,
                         args.gcps, args.ref_img, args.debug, args.show)


def transform_func(args):
    print("Transform function for model:", args)

    if args.model_name == C.SATELLITE_MODELS.RFM:
        from geoCosiCorr3D.geoRFM.RFM import RFM
        model_data = RFM(args.rfm_fn, dem_fn=args.dem_fn, debug=True)
        if not args.inv:
            res = np.asarray(model_data.i2g(args.x, args.y)).T
            print(f'lons:{res[:, 0]}')
            print(f'lat:{res[:, 1]}')
            print(f'alt:{res[:, 2]}')
        else:
            res = np.asarray(model_data.g2i(args.x, args.y, )).T
            print(f'cols:{res[:, 0]}')
            print(f'lines:{res[:, 1]}')
    if args.model_name == C.SATELLITE_MODELS.RSM:
        raise NotImplementedError


def correlate_func(args):
    print(f'Executing correlation module :{args}')
    corr_config = {}

    if args.method == C.CORR_METHODS.FREQUENCY_CORR.value:
        corr_config = {
            "correlator_name": C.CORR_METHODS.FREQUENCY_CORR.value,
            "correlator_params": {
                "window_size": args.window_size,
                "step": args.step,
                "grid": args.grid,
                "mask_th": args.mask_th,
                "nb_iters": args.nb_iters
            }
        }
    elif args.method == C.CORR_METHODS.SPATIAL_CORR.value:
        corr_config = {
            "correlator_name": C.CORR_METHODS.SPATIAL_CORR.value,
            "correlator_params": {
                "window_size": args.window_size,
                "step": args.step,
                "grid": args.grid,
                "search_range": args.search_range
            }
        }

    Correlate(base_image_path=args.base_image,
              target_image_path=args.target_image,
              base_band=args.base_band,
              target_band=args.target_band,
              output_corr_path=args.output_path,
              corr_config=corr_config,
              corr_show=args.show,
              pixel_based_correlation=args.pixel_based,
              vmin=args.vmin,
              vmax=args.vmax
              )


def batch_correlate_func(args):
    geoCosiCorr3DLog('Batch Correlation', os.getcwd())
    logging.info(f'Executing batch correlation module :{args}')

    base_images = []
    for pattern in args.base_images.split(','):
        base_images.extend(glob.glob(pattern))
    target_images = []
    for pattern in args.target_images.split(','):
        target_images.extend(glob.glob(pattern))

    base_bands = args.base_bands if args.base_bands else [1] * len(base_images)
    target_bands = args.target_bands if args.target_bands else [1] * len(target_images)

    if not args.serial and not args.all:
        args.all = True

    if args.serial:
        if len(base_images) != len(target_images):
            raise ValueError(f"Input_base_images:{len(base_images)} and target_images:{len(target_images)} -- "
                             f"The number of base images and target images must be equal when using the --serial option.")

        num_correlations = len(base_images)
        logging.info(f'Number of possible correlations (serial): {num_correlations}')
        for base_image, target_image, base_band, target_band in zip(base_images, target_images, base_bands,
                                                                    target_bands):
            correlate_func(argparse.Namespace(base_image=base_image,
                                              target_image=target_image,
                                              base_band=base_band,
                                              target_band=target_band,
                                              output_path=args.output_path,
                                              method=args.method,
                                              window_size=args.window_size,
                                              step=args.step,
                                              grid=args.grid,
                                              show=args.show,
                                              pixel_based=args.pixel_based,
                                              vmin=args.vmin,
                                              vmax=args.vmax,
                                              mask_th=args.mask_th,
                                              nb_iters=args.nb_iters,
                                              search_range=args.search_range
                                              ))
    elif args.all:
        num_correlations = len(base_images) * len(target_images)
        logging.info(f'Number of possible correlations (all): {num_correlations}')
        for (base_image, base_band), (target_image, target_band) in itertools.product(zip(base_images, base_bands),
                                                                                      zip(target_images, target_bands)):
            correlate_func(argparse.Namespace(base_image=base_image,
                                              target_image=target_image,
                                              base_band=base_band,
                                              target_band=target_band,
                                              output_path=args.output_path,
                                              method=args.method,
                                              window_size=args.window_size,
                                              step=args.step,
                                              grid=args.grid,
                                              show=args.show,
                                              pixel_based=args.pixel_based,
                                              vmin=args.vmin,
                                              vmax=args.vmax,
                                              mask_th=args.mask_th,
                                              nb_iters=args.nb_iters,
                                              search_range=args.search_range))


def multiband_correlate_func(args):
    geoCosiCorr3DLog('Multiband Correlation', os.getcwd())
    logging.info(f'Executing multiband correlation module :{args}')

    # Load the input image and get the number of bands
    input_image = args.input_img
    input_image_name = os.path.splitext(os.path.basename(input_image))[0]
    raster_info = geo_utils.cRasterInfo(input_raster_path=args.input_img)
    num_bands = raster_info.band_number
    logging.info(f'Number of bands: {num_bands}')

    if num_bands < 2:
        raise ValueError("The input image must have at least two bands for multiband correlation.")

    if args.band_combination:
        band_combinations = [tuple(map(int, comb.split(','))) for comb in args.band_combination.split(';')]
    else:
        band_combinations = [(i, j) for i in range(1, num_bands + 1) for j in range(i + 1, num_bands + 1)]

    logging.info(f'Number of band combinations: {len(band_combinations)}')

    for base_band, target_band in band_combinations:
        if not args.output_path or os.path.isdir(args.output_path):
            output_filename = f"corr_{input_image_name}_bands_{base_band}_{target_band}.tif"
            output_path = os.path.join(args.output_path if args.output_path else os.getcwd(), output_filename)
        else:
            raise ValueError(f"Output path {args.output_path} is not a directory.")

        correlate_func(argparse.Namespace(base_image=input_image,
                                          target_image=input_image,
                                          base_band=base_band,
                                          target_band=target_band,
                                          output_path=output_path,
                                          method=args.method,
                                          window_size=args.window_size,
                                          step=args.step,
                                          grid=args.grid,
                                          show=args.show,
                                          pixel_based=args.pixel_based,
                                          vmin=args.vmin,
                                          vmax=args.vmax,
                                          mask_th=args.mask_th,
                                          nb_iters=args.nb_iters,
                                          search_range=args.search_range
                                          ))


def ortho_subparser(subparsers):
    ortho_parser = subparsers.add_parser('ortho', help='Orthorectification process')
    ortho_parser.add_argument('input_img', type=str, help='Input file for ortho')
    ortho_parser.add_argument('--o_ortho', type=str, default=os.getcwd(),
                              help='Output path for ortho. Defaults to the current working directory.')
    ortho_parser.add_argument('--corr_model', type=str, default=None, help='Correction model path (None)')
    ortho_parser.add_argument('--dem', type=str, default=None, help='DEM path (None)')
    ortho_parser.add_argument('--gsd', type=float, default=None, help='Output file for ortho (None)')
    ortho_parser.add_argument('--resampling_method', type=str, default=C.Resampling_Methods.SINC,
                              choices=C.GEOCOSICORR3D_RESAMLING_METHODS, help='Resampling method (SINC)')

    ortho_parser.add_argument("--debug", action="store_true")
    ortho_parser.add_argument("--show", action="store_true")

    ortho_parser.add_argument("--refine", action="store_true",
                              help="Refine model, this require GCPs or reference imagery to collect GCPs")
    ortho_parser.add_argument('--ref_img', type=str, default=None, help='Reference Ortho image (None)')
    ortho_parser.add_argument('--gcps', type=str, default=None, help='GCPs file (None)')

    model_subparsers = ortho_parser.add_subparsers(title='model', dest='model_name', metavar='<model_name>',
                                                   required=True)

    rfm_parser = model_subparsers.add_parser(C.SATELLITE_MODELS.RFM, help="RFM model specific arguments")
    rfm_parser.add_argument('rfm_fn', type=str, help="RFM file name (.tiff or .TXT)")
    rfm_parser.set_defaults(func=ortho_func)

    rsm_parser = model_subparsers.add_parser(C.SATELLITE_MODELS.RSM, help="RSM model specific arguments")
    rsm_parser.add_argument('sat_id', type=str, choices=C.GEOCOSICORR3D_SENSORS_LIST, help="Sat-name")
    rsm_parser.add_argument('rsm_fn', type=str, help="Specifies the path to the .xml DMP file. Additional formats "
                                                     "are supported in GeoCosiCorr3D.pro.")
    rsm_parser.set_defaults(func=ortho_func)


def transform_subparser(subparsers):
    transform_parser = subparsers.add_parser('transform', help='Transformation')

    transform_parser.add_argument('x', type=parse_list, help="list: x=cols and if with invert flag: lon")
    transform_parser.add_argument('y', type=parse_list, help="list: y=lines and if with invert flag: lat")
    transform_parser.add_argument("--inv", action="store_true", help="Transform form ground to image space.")
    transform_parser.add_argument('--dem_fn', type=str, default=None, help="DEM file name (None)")

    model_subparsers = transform_parser.add_subparsers(title='model', dest='model_name', metavar='<model_name>',
                                                       required=True)

    rfm_parser = model_subparsers.add_parser(C.SATELLITE_MODELS.RFM, help="RFM model specific arguments")
    rfm_parser.add_argument('rfm_fn', type=str, help="RFM file name (.tiff or .TXT)")
    rfm_parser.set_defaults(func=transform_func)

    # RSM model specific parser setup
    rsm_parser = model_subparsers.add_parser(C.SATELLITE_MODELS.RSM, help="RSM model specific arguments")
    rsm_parser.add_argument('sat_id', type=str, help="Sat-name")
    rsm_parser.add_argument('rsm_fn', type=str, help="Specifies the path to the .xml DMP file. Additional formats "
                                                     "are supported in GeoCosiCorr3D.pro"
                            )
    rsm_parser.set_defaults(func=transform_func)


def correlate_subparser(subparsers):
    correlate_parser = subparsers.add_parser('correlate', help='Correlation')
    correlate_parser.add_argument("base_image", type=str, help="Path to the base image.")
    correlate_parser.add_argument("target_image", type=str, help="Path to the target image.")
    correlate_parser.add_argument("--base_band", type=int, default=1, help="Base image band.")
    correlate_parser.add_argument("--target_band", type=int, default=1, help="Target image band.")
    correlate_parser.add_argument("--output_path", type=str, default=C.SOFTWARE.WKDIR, help="Output correlation path.")
    correlate_parser.add_argument("--method", type=str,
                                  choices=[C.CORR_METHODS.FREQUENCY_CORR.value, C.CORR_METHODS.SPATIAL_CORR.value],
                                  default=C.CORR_METHODS.FREQUENCY_CORR.value,
                                  help="Correlation method to use.")
    correlate_parser.add_argument("--window_size", type=int, nargs=4, default=[64, 64, 64, 64],
                                  help="Window size. (Default [64])")
    correlate_parser.add_argument("--step", type=int, nargs=2, default=[8, 8], help="Step size. (Default [8,8])")
    correlate_parser.add_argument("--grid", action="store_true", help="Use grid.")
    correlate_parser.add_argument("--show", action="store_true", help="Show correlation. (Default False)")
    correlate_parser.add_argument("--pixel_based", action="store_true", help="Enable pixel-based correlation.")
    correlate_parser.add_argument("--vmin", type=float, default=-1,
                                  help="Minimum value for correlation plot. (Default -1)")
    correlate_parser.add_argument("--vmax", type=float, default=1,
                                  help="Maximum value for correlation plot.(Default 1)")

    # Specific arguments for frequency method
    freq_group = correlate_parser.add_argument_group("Frequency method arguments")
    freq_group.add_argument("--mask_th", type=float, default=0.95, help="Mask threshold (only for frequency method).")
    freq_group.add_argument("--nb_iters", type=int, default=4, help="Number of iterations (only for frequency method).")

    # Specific arguments for spatial method
    spatial_group = correlate_parser.add_argument_group("Spatial method arguments")
    spatial_group.add_argument("--search_range", type=int, nargs=2, help="Search range (only for spatial method).")

    correlate_parser.set_defaults(func=correlate_func)


def batch_correlate_subparser(subparsers):
    batch_correlate_parser = subparsers.add_parser('batch_correlate', help='Batch Correlation')
    batch_correlate_parser.add_argument("base_images", type=str, help="Comma-separated list of paths to base images.")
    batch_correlate_parser.add_argument("target_images", type=str,
                                        help="Comma-separated list of paths to target images.")
    batch_correlate_parser.add_argument("--serial", action="store_true", help="Correlate images with the same index.")
    batch_correlate_parser.add_argument("--all", action="store_true", help="Correlate all possible combinations.")
    batch_correlate_parser.add_argument("--base_bands", type=int, nargs='+', help="List of base image bands.")
    batch_correlate_parser.add_argument("--target_bands", type=int, nargs='+', help="List of target image bands.")
    batch_correlate_parser.add_argument("--output_path", type=str, default=C.SOFTWARE.WKDIR,
                                        help="Output correlation path.")
    batch_correlate_parser.add_argument("--method", type=str, choices=[C.CORR_METHODS.FREQUENCY_CORR.value,
                                                                       C.CORR_METHODS.SPATIAL_CORR.value],
                                        default=C.CORR_METHODS.FREQUENCY_CORR.value, help="Correlation method to use.")
    batch_correlate_parser.add_argument("--window_size", type=int, nargs=4, default=[64, 64, 64, 64],
                                        help="Window size. (Default [64])")
    batch_correlate_parser.add_argument("--step", type=int, nargs=2, default=[8, 8], help="Step size. (Default [8,8])")
    batch_correlate_parser.add_argument("--grid", action="store_true", help="Use grid.")
    batch_correlate_parser.add_argument("--show", action="store_true", help="Show correlation. (Default False)")
    batch_correlate_parser.add_argument("--pixel_based", action="store_true", help="Enable pixel-based correlation.")
    batch_correlate_parser.add_argument("--vmin", type=float, default=-1,
                                        help="Minimum value for correlation plot. (Default -1)")
    batch_correlate_parser.add_argument("--vmax", type=float, default=1,
                                        help="Maximum value for correlation plot.(Default 1)")

    # Specific arguments for frequency method
    freq_group = batch_correlate_parser.add_argument_group("Frequency method arguments")
    freq_group.add_argument("--mask_th", type=float, default=0.95, help="Mask threshold (only for frequency method).")
    freq_group.add_argument("--nb_iters", type=int, default=4, help="Number of iterations (only for frequency method).")

    # Specific arguments for spatial method
    spatial_group = batch_correlate_parser.add_argument_group("Spatial method arguments")
    spatial_group.add_argument("--search_range", type=int, nargs=2, help="Search range (only for spatial method).")

    batch_correlate_parser.set_defaults(func=batch_correlate_func)


def multiband_correlate_subparser(subparsers):
    multiband_correlate_parser = subparsers.add_parser('multi_band_correlation', help='Multiband Correlation')
    multiband_correlate_parser.add_argument("input_img", type=str, help="Path to the input image.")
    multiband_correlate_parser.add_argument("--band_combination", type=str,
                                            help="Semicolon-separated list of band combinations (e.g., '1,2;3,4').")
    multiband_correlate_parser.add_argument("--output_path", type=str, default=C.SOFTWARE.WKDIR,
                                            help="Output correlation path.")
    multiband_correlate_parser.add_argument("--method", type=str, choices=[C.CORR_METHODS.FREQUENCY_CORR.value,
                                                                           C.CORR_METHODS.SPATIAL_CORR.value],
                                            default=C.CORR_METHODS.FREQUENCY_CORR.value,
                                            help="Correlation method to use.")
    multiband_correlate_parser.add_argument("--window_size", type=int, nargs=4, default=[64, 64, 64, 64],
                                            help="Window size. (Default [64])")
    multiband_correlate_parser.add_argument("--step", type=int, nargs=2, default=[8, 8],
                                            help="Step size. (Default [8,8])")
    multiband_correlate_parser.add_argument("--grid", action="store_true", help="Use grid.")
    multiband_correlate_parser.add_argument("--show", action="store_true", help="Show correlation. (Default False)")
    multiband_correlate_parser.add_argument("--pixel_based", action="store_true",
                                            help="Enable pixel-based correlation.")
    multiband_correlate_parser.add_argument("--vmin", type=float, default=-1,
                                            help="Minimum value for correlation plot. (Default -1)")
    multiband_correlate_parser.add_argument("--vmax", type=float, default=1,
                                            help="Maximum value for correlation plot.(Default 1)")

    # Specific arguments for frequency method
    freq_group = multiband_correlate_parser.add_argument_group("Frequency method arguments")
    freq_group.add_argument("--mask_th", type=float, default=0.95, help="Mask threshold (only for frequency method).")
    freq_group.add_argument("--nb_iters", type=int, default=4, help="Number of iterations (only for frequency method).")

    # Specific arguments for spatial method
    spatial_group = multiband_correlate_parser.add_argument_group("Spatial method arguments")
    spatial_group.add_argument("--search_range", type=int, nargs=2, help="Search range (only for spatial method).")

    multiband_correlate_parser.set_defaults(func=multiband_correlate_func)

def cosicorr():
    parser = argparse.ArgumentParser(prog='cosicorr3d', description='GeoCosiCorr3D CLI',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    subparsers = parser.add_subparsers(title='modules', dest='module', metavar='<module>')

    ortho_subparser(subparsers)
    transform_subparser(subparsers)
    correlate_subparser(subparsers)
    batch_correlate_subparser(subparsers)
    multiband_correlate_subparser(subparsers)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    cosicorr()
